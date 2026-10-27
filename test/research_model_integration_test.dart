import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:eos/core/widgets/research_model_card.dart';
import 'package:eos/data/api/api_client.dart';
import 'package:eos/data/deidentify.dart';
import 'package:eos/data/research_model_inputs.dart';
import 'package:eos/domain/eoscal_calculator.dart';
import 'package:eos/presentation/patient_state.dart';

PatientParameters fixture() {
  final recordedAt = DateTime.now().toUtc();
  return PatientParameters(
    id: 'synthetic-id',
    name: 'Synthetic private name',
    mrn: 'SYNTHETIC-MRN',
    gestationalAgeWeeks: 36,
    birthDateTime: DateTime.now().subtract(const Duration(hours: 12)),
    maternalTemperature: 37,
    romHours: 1,
    gbsPositive: false,
    adequateIntrapartumAntibiotics: false,
    clinicalChorioamnionitis: false,
    deliveryMode: 'Caesarean',
    respiratoryDistress: 'None',
    oxygenNeed: 'None',
    apgar5Min: 8,
    poorPerfusion: false,
    neonatalTemperature: 36.8,
    neurologicalStatus: 'Normal',
    birthWeightGrams: 3200,
    // Clinical lab values must not be silently rescaled into undocumented units.
    wbcCount: 12000,
    plateletCount: 220000,
    crpLevel: 5,
    pctLevel: .7,
    researchModelInputs: const {
      'Sex': 'Male',
      'HR': 150,
      'Resp': 50,
      'SpO2': 97,
    },
    assessmentRecordedAt: recordedAt,
    researchInputsReviewedAt: recordedAt,
  );
}

class _PatientRecorder extends PatientsNotifier {
  PatientParameters? saved;
  @override
  Future<void> updatePatient(PatientParameters patient) async {
    saved = patient;
  }
}

class _ModelAdapter implements HttpClientAdapter {
  final Map<String, dynamic> response;
  Map<String, dynamic>? sent;
  String? path;
  _ModelAdapter(this.response);
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    path = options.path;
    sent = Map<String, dynamic>.from(options.data as Map);
    return ResponseBody.fromString(
      jsonEncode(response),
      200,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  final metadata =
      jsonDecode(
            File(
              'test/fixtures/research_model_contract.json',
            ).readAsStringSync(),
          )
          as Map<String, dynamic>;

  test(
    'Payload matches every installed feature and excludes identity and guessed units',
    () {
      final values = ResearchModelInputs.prefill(fixture(), 12);
      expect(values.keys.toSet(), ResearchModelInputs.names);
      expect(values['Birth_Weight'], 3.2);
      expect(values['Delivery_Mode'], 'Cesarean');
      expect(values['Postnatal_Age'], 0);
      expect(values['HR'], 150);
      for (final key in [
        'Oxygen',
        'WBC',
        'CRP',
        'PCT',
        'Platelets',
        'Lactate',
        'Hemoglobin',
      ]) {
        expect(
          values[key],
          isNull,
          reason: 'Undocumented dataset units must not be guessed',
        );
      }
      final request = ResearchModelInputs.payload(values, 12);
      final encoded = jsonEncode(request);
      expect(encoded, isNot(contains('SYNTHETIC-MRN')));
      expect(encoded, isNot(contains('Synthetic private name')));
      expect(encoded, isNot(contains('synthetic-id')));
      expect(request['purpose'], 'research');
      expect(
        (metadata['input_contract'] as List).map((f) => f['name']).toSet(),
        ResearchModelInputs.names,
      );
      expect(
        () => ResearchModelInputs.payload({...values, 'name': 'private'}, 12),
        throwsArgumentError,
      );
      expect(
        () => ResearchModelInputs.payload(values, 72),
        throwsArgumentError,
      );
    },
  );

  test(
    'Birth weight and research inputs survive patient storage and reassessment',
    () {
      final patient = fixture();
      final stored = PatientsNotifier.encodeRecord(patient);
      final restored = PatientsNotifier.decodeRecord(
        jsonDecode(jsonEncode(stored)) as Map<String, dynamic>,
      );
      expect(restored.birthWeightGrams, 3200);
      expect(restored.researchModelInputs['HR'], 150);
      expect(restored.researchModelInputs['Sex'], 'Male');
      expect(restored.hasCurrentResearchMeasurements, isTrue);
      expect(
        restored.researchInputsReviewedAt,
        patient.researchInputsReviewedAt,
      );
      expect(
        restored.copyWith(crpLevel: 6).researchModelInputs,
        patient.researchModelInputs,
      );
      final old = Map<String, dynamic>.from(stored)
        ..remove('researchModelInputs')
        ..remove('birthWeightGrams')
        ..remove('careSetting');
      final legacy = PatientsNotifier.decodeRecord(old);
      expect(legacy.researchModelInputs, isEmpty);
      expect(legacy.birthWeightGrams, isNull);
    },
  );

  test('New measured vitals reach the allowlisted RAG snapshot', () {
    final snapshot = DeidentifiedPatient.fromPatient(fixture()).toJson();
    expect(snapshot['heart_rate'], 150);
    expect(snapshot['respiratory_rate'], 50);
    expect(snapshot['spo2'], 97);
    expect(snapshot.containsKey('Sex'), isFalse);
    final laterAssessment = fixture().copyWith(
      assessmentRecordedAt: DateTime.now().add(const Duration(hours: 1)),
    );
    final laterSnapshot = DeidentifiedPatient.fromPatient(
      laterAssessment,
    ).toJson();
    expect(laterSnapshot.containsKey('heart_rate'), isFalse);
    expect(laterSnapshot.containsKey('respiratory_rate'), isFalse);
    expect(laterSnapshot.containsKey('spo2'), isFalse);
    final unknownTemp = fixture().copyWith(
      researchModelInputs: const {'Temp': null},
    );
    expect(
      DeidentifiedPatient.fromPatient(
        unknownTemp,
      ).toJson().containsKey('neonatal_temperature'),
      isFalse,
    );
  });

  testWidgets('Review dialog exposes all model inputs with explicit unknowns', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        child: MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: ResearchModelCard(patient: fixture(), metadata: metadata),
            ),
          ),
        ),
      ),
    );
    await tester.tap(find.text('Review model inputs & predict'));
    await tester.pumpAndSettle();
    expect(find.byType(TextFormField), findsNWidgets(16));
    expect(find.byType(DropdownButtonFormField<String>), findsNWidgets(2));
    expect(find.text('Unknown / not measured'), findsNWidgets(12));
    expect(find.text('Review trained-model inputs'), findsOneWidget);
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('Cancel'));
    await tester.pumpAndSettle();
  });

  testWidgets(
    'Reviewed inputs are saved, posted to the model route and displayed',
    (tester) async {
      dotenv.testLoad(fileInput: 'API_BASE_URL=http://127.0.0.1:8000');
      final data =
          jsonDecode(
                File(
                  'test/fixtures/research_prediction_case.json',
                ).readAsStringSync(),
              )
              as Map<String, dynamic>;
      final values = Map<String, dynamic>.from(
        (data['request'] as Map)['values'] as Map,
      );
      final response = Map<String, dynamic>.from(data['response'] as Map);
      final adapter = _ModelAdapter(response);
      final originalAdapter = apiClient.dio.httpClientAdapter;
      apiClient.dio.httpClientAdapter = adapter;
      final recorder = _PatientRecorder();
      await tester.pumpWidget(
        ProviderScope(
          overrides: [patientsProvider.overrideWith((ref) => recorder)],
          child: MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: ResearchModelCard(
                  patient: fixture().copyWith(researchModelInputs: values),
                  metadata: metadata,
                ),
              ),
            ),
          ),
        ),
      );
      await tester.tap(find.text('Review model inputs & predict'));
      await tester.pumpAndSettle();
      final confirmation = find.text(
        'I reviewed each measurement, its units, and the fields marked unknown for this assessment.',
      );
      await tester.ensureVisible(confirmation);
      await tester.tap(confirmation);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Save inputs & predict'));
      await tester.pumpAndSettle();
      expect(adapter.path, '/api/v1/research/model/predict');
      expect(
        (adapter.sent!['values'] as Map).keys.toSet(),
        ResearchModelInputs.names,
      );
      expect((adapter.sent!['values'] as Map)['Birth_Weight'], 3.2);
      expect(adapter.sent!['reviewed_inputs'], isTrue);
      expect(recorder.saved!.researchModelInputs['Lactate'], 1.5);
      expect(response['probability'] as num, greaterThan(0));
      expect(response['probability'] as num, lessThan(0.001));
      const percent = '<0.1%';
      expect(find.text(percent), findsOneWidget);
      expect(tester.takeException(), isNull);
      apiClient.dio.httpClientAdapter = originalAdapter;
      await tester.pumpWidget(const SizedBox());
    },
  );
}
