import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:eos/data/longitudinal_inputs.dart';
import 'package:eos/presentation/screens/longitudinal_inputs_screen.dart';

Map<String, dynamic> observation(double age, double value) => {
  'field': 'heart_rate',
  'age_hours': age,
  'available_age_hours': age,
  'value': value,
};

void main() {
  final contract =
      jsonDecode(
            File('test/fixtures/longitudinal_contract.json').readAsStringSync(),
          )
          as Map<String, dynamic>;

  test('Mobile field keys exactly match the server input contract', () {
    expect(
      (contract['sequence_fields'] as List).map((f) => f['key']).toSet(),
      LongitudinalInputs.measurements,
    );
    expect(
      (contract['context_fields'] as List).map((f) => f['key']).toSet(),
      LongitudinalInputs.contextFields,
    );
    final payload = LongitudinalInputs.payload(
      ageHours: 4,
      observations: [observation(1, 120), observation(4, 140)],
      context: {for (final k in LongitudinalInputs.contextFields) k: null},
    );
    expect((payload['context'] as Map).values.every((v) => v == null), isTrue);
    expect((payload['sequence'] as Map)['observations'][0]['age_hours'], 1);
    expect(payload.containsKey('patient_name'), isFalse);
  });

  test(
    'Future values, duplicate times and identifiers fail before network',
    () {
      final context = {
        for (final k in LongitudinalInputs.contextFields) k: null,
      };
      for (final rows in [
        [observation(5, 120)],
        [observation(1, 120), observation(1, 130)],
        [
          {...observation(1, 120), 'patient_name': 'private'},
        ],
      ]) {
        expect(
          () => LongitudinalInputs.payload(
            ageHours: 4,
            observations: rows,
            context: context,
          ),
          throwsArgumentError,
        );
      }
    },
  );

  test('A submitted history snapshot cannot change with later form edits', () {
    final rows = [observation(1, 120)];
    final context = {for (final k in LongitudinalInputs.contextFields) k: null};
    final payload = LongitudinalInputs.payload(
      ageHours: 4,
      observations: rows,
      context: context,
    );
    rows[0]['value'] = 180;
    expect(payload['sequence']['observations'][0]['value'], 120);
  });

  testWidgets(
    'Research workflow keeps timed history and unknown maternal fields',
    (tester) async {
      Map<String, dynamic>? submitted;
      await tester.pumpWidget(
        MaterialApp(
          home: LongitudinalInputsScreen(
            loadContract: () async => contract,
            previewInputs: (body) async {
              submitted = body;
              return {
                'notice': 'Prediction withheld: model quality gate.',
                'trends': {
                  'heart_rate': {
                    'count': 2.0,
                    'last': 140.0,
                    'delta': 20.0,
                    'slope_per_hour': 20 / 3,
                  },
                },
              };
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('Research model — prediction withheld'), findsOneWidget);
      await tester.enterText(
        find.byKey(const ValueKey('Age at assessment (hours)')),
        '4',
      );
      await tester.scrollUntilVisible(
        find.text('Add timed measurement'),
        400,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.enterText(
        find.byKey(const ValueKey('Age when measured (hours)')),
        '1',
      );
      await tester.enterText(
        find.byKey(const ValueKey('Age when available (hours)')),
        '1',
      );
      await tester.enterText(
        find.byKey(const ValueKey('Value (beats/min)')),
        '120',
      );
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await Scrollable.ensureVisible(
        tester.element(find.text('Add timed measurement')),
        alignment: 0.5,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add timed measurement'));
      await tester.pumpAndSettle();
      await tester.enterText(
        find.byKey(const ValueKey('Age when measured (hours)')),
        '4',
      );
      await tester.enterText(
        find.byKey(const ValueKey('Age when available (hours)')),
        '4',
      );
      await tester.enterText(
        find.byKey(const ValueKey('Value (beats/min)')),
        '140',
      );
      FocusManager.instance.primaryFocus?.unfocus();
      await tester.pumpAndSettle();
      await Scrollable.ensureVisible(
        tester.element(find.text('Add timed measurement')),
        alignment: 0.5,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Add timed measurement'));
      await tester.pumpAndSettle();
      await tester.scrollUntilVisible(
        find.text('Review history and inputs'),
        600,
        scrollable: find.byType(Scrollable).first,
      );
      await tester.tap(find.text('Review history and inputs'));
      await tester.pumpAndSettle();
      expect(submitted, isNotNull);
      expect((submitted!['sequence']['observations'] as List).length, 2);
      expect(submitted!['context']['gbs_positive'], isNull);
      expect(
        find.text('Prediction withheld: model quality gate.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
