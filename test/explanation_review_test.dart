import 'dart:convert';
import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:eos/data/api/api_client.dart';
import 'package:eos/domain/eoscal_calculator.dart';
import 'package:eos/presentation/screens/explanation_screen.dart';
import 'research_model_integration_test.dart' as fixtures;

class _ReviewAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions request,
    Stream<Uint8List>? stream,
    Future<void>? cancel,
  ) async {
    final data = request.path == '/health'
        ? {'status': 'ok'}
        : {
            'clinical_summary': 'Synthetic source-supported review.',
            'evidence_summary': 'Recorded observations require review.',
            'per_driver_explanations': [
              {
                'factor': 'Recorded course',
                'explanation': 'Two observations are available.',
              },
            ],
            'recommended_actions': ['Review the recorded observations.'],
            'monitoring_plan': 'Review observed changes.',
            'escalation_criteria': 'Use the cited assessment pathway.',
            'citation_list': [],
            'rag_chunks': [],
            'model_version': 'test-only',
            'fallback_used': false,
            'evidence_labels': [],
            'antibiotic_plan': {
              'required': false,
              'decision_status': 'evidence_for_review',
              'urgency': 'Prescriber review',
              'regimen': ['A source-supported option for clinician review.'],
              'duration': 'Document the individual decision.',
              'stop_criteria': 'No stopping order is issued.',
            },
          };
    return ResponseBody.fromString(
      jsonEncode(data),
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
  testWidgets(
    'False order flag never becomes a claim that antibiotics are not indicated',
    (tester) async {
      dotenv.testLoad(fileInput: 'API_BASE_URL=http://127.0.0.1:8000');
      final previous = apiClient.dio.httpClientAdapter;
      apiClient.dio.httpClientAdapter = _ReviewAdapter();
      addTearDown(() => apiClient.dio.httpClientAdapter = previous);
      final p = fixtures.fixture();
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: ExplanationScreen(
              patient: p,
              result: EoscalCalculator.calculate(p),
              activeGuideline: 'NICE',
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
      final title = find.text('Antibiotic Plan');
      await tester.ensureVisible(title);
      await tester.pumpAndSettle();
      expect(find.text('Prescriber review'), findsWidgets);
      expect(find.text('Not indicated'), findsNothing);
      expect(
        find.textContaining('Antibiotics are not currently indicated'),
        findsNothing,
      );
      expect(
        find.text('A source-supported option for clinician review.'),
        findsOneWidget,
      );
    },
  );
}
