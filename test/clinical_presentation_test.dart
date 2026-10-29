import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:eos/core/widgets/clinical_text.dart';
import 'package:eos/core/widgets/evidence_citation.dart';
import 'package:eos/core/widgets/shap_waterfall.dart';
import 'package:eos/data/models/rag_chunk.dart';

void main() {
  test(
    'Ordered clinical steps retain their numbers and decimal measurements',
    () {
      final blocks = clinicalTextBlocks(
        '1. Obtain missing observations.\n2. Review results.\n0.5 mg/L',
      );
      expect(blocks[0].marker, '1.');
      expect(blocks[1].marker, '2.');
      expect(blocks[2].text, '0.5 mg/L');
      expect(blocks[2].bullet, isFalse);
    },
  );
  testWidgets(
    'Formatted bullets retain tappable evidence and exact source text',
    (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: EvidenceCitationText(
              text:
                  '**Source-supported point**\n• Keep the condition attached to its evidence. [E1]',
              labels: {
                'E1': EvidenceLabelRef(
                  label: 'E1',
                  chunkId: 'fixture',
                  source: 'Fixture',
                  sourceName: 'Fixture',
                  section: 'Review',
                  snippet:
                      'Exact quoted source text. Do not remove this condition.',
                ),
              },
            ),
          ),
        ),
      );
      await tester.tap(find.text('E1'));
      await tester.pumpAndSettle();
      expect(
        find.text('Exact quoted source text. Do not remove this condition.'),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
  test(
    'Formatting retains conjunctive conditions, unknowns and evidence labels',
    () {
      const text =
          'Review only if: • the culture is negative and • the condition is reassuring. [E2]\n**Unknown:** treatment start time.';
      final blocks = clinicalTextBlocks(text);
      expect(blocks.where((b) => b.bullet).length, 2);
      expect(blocks.map((b) => b.text).join(' '), contains('negative and'));
      expect(blocks.map((b) => b.text).join(' '), contains('[E2]'));
      expect(blocks.map((b) => b.text).join(' '), contains('Unknown:'));
      expect(clinicalTextBlocks('0.5 mg/kg [E1]').single.bullet, isFalse);
      expect(clinicalTextBlocks('－1.2 measured value').single.bullet, isFalse);
      expect(
        clinicalTextBlocks('• Parent condition － nested condition').last.nested,
        isTrue,
      );
    },
  );
  test(
    'Waterfall groups smaller inputs without losing signed contributions',
    () {
      final steps = shapWaterfallSteps(.5, .65, [
        {'feature': 'A', 'contribution': .2},
        {'feature': 'B', 'contribution': -.1},
        {'feature': 'C', 'contribution': .05},
      ], maxFeatures: 1);
      expect(steps[2].label, 'Other 2 inputs');
      expect(steps[2].end, closeTo(.65, 1e-10));
      expect(steps.last.end, .65);
      expect(
        () => shapWaterfallSteps(.5, .9, [
          {'feature': 'A', 'contribution': .1},
        ]),
        throwsArgumentError,
      );
    },
  );
  testWidgets(
    'Clinical bullets and waterfall fit a narrow screen with enlarged text',
    (tester) async {
      tester.view.physicalSize = const Size(360, 1000);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        MaterialApp(
          home: MediaQuery(
            data: const MediaQueryData(textScaler: TextScaler.linear(1.4)),
            child: Scaffold(
              body: SingleChildScrollView(
                child: Column(
                  children: [
                    const EvidenceCitationText(
                      text:
                          '**Investigations**\n• Review the recorded sample. [E1]\n• Preserve all eligibility conditions.',
                      labels: {},
                    ),
                    ShapWaterfall(
                      baseline: .5,
                      prediction: .999999,
                      contributions: const [
                        {'feature': 'Gestational_Age', 'contribution': .55},
                        {'feature': 'Resp', 'contribution': -.050001},
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(find.text('How inputs change the score'), findsOneWidget);
      expect(find.text('>99.9%'), findsOneWidget);
      expect(find.text('Research model score'), findsNothing);
      expect(tester.takeException(), isNull);
    },
  );
}
