import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:eos/data/deidentify.dart';
import 'package:eos/domain/eoscal_calculator.dart';

PatientParameters patient(String setting) => PatientParameters(
  id: 'synthetic-id',
  name: 'Private synthetic name',
  mrn: 'PRIVATE-SYNTHETIC-MRN',
  gestationalAgeWeeks: 38,
  birthDateTime: DateTime.now().subtract(const Duration(hours: 12)),
  maternalTemperature: 37,
  romHours: 2,
  gbsPositive: false,
  adequateIntrapartumAntibiotics: false,
  clinicalChorioamnionitis: false,
  deliveryMode: 'Vaginal',
  respiratoryDistress: 'None',
  oxygenNeed: 'None',
  apgar5Min: 8,
  poorPerfusion: false,
  neonatalTemperature: 36.8,
  neurologicalStatus: 'Normal',
  careSetting: setting,
);

void main() {
  test(
    'RAG receives the recorded care setting without patient identifiers',
    () {
      for (final setting in ['hospital', 'outpatient_no_referral']) {
        final p = patient(setting);
        final body = buildRiskPayload(p, EoscalCalculator.calculate(p));
        final snapshot = body['patient'] as Map<String, dynamic>;
        expect(
          snapshot['care_setting'],
          setting == 'hospital' ? 'hospital' : 'non_hospital',
        );
        expect(snapshot['age_hours'], greaterThan(0));
        expect(jsonEncode(body), isNot(contains(p.name)));
        expect(jsonEncode(body), isNot(contains(p.mrn)));
        expect(snapshot, isNot(contains('id')));
        expect(snapshot, isNot(contains('birth_date_time')));
        expect(body, isNot(contains('combined_score')));
        expect(body, isNot(contains('probability_per_1000')));
      }
    },
  );
  test('Explicit culture results reach RAG without inventing timing', () {
    final base = patient('hospital');
    for (final p in [
      base,
      base.copyWith(bloodCulturePositive: false),
      base.copyWith(bloodCulturePositive: true),
    ]) {
      final snapshot =
          buildRiskPayload(p, EoscalCalculator.calculate(p))['patient']
              as Map<String, dynamic>;
      expect(
        snapshot['culture_status'],
        p.bloodCulturePositive == null
            ? 'unknown'
            : p.bloodCulturePositive!
            ? 'positive'
            : 'negative',
      );
      expect(snapshot, isNot(contains('culture_incubation_hours')));
      expect(snapshot, isNot(contains('antibiotic_exposure_hours')));
    }
  });
}
