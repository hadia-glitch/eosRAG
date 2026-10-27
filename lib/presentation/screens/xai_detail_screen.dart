import 'package:flutter/material.dart';
import '../../domain/eoscal_calculator.dart';
import '../../data/api/api_client.dart';
import '../../data/research_model_inputs.dart';
import '../../core/widgets/shap_waterfall.dart';

/// Explain the served ML artifact; retired point-score tables are not model XAI.
class XaiDetailScreen extends StatefulWidget {
  final PatientParameters? patient;
  final Map<String, dynamic>? explanation;
  final ScoreDriver? driver;
  final EoscalResult? result;
  const XaiDetailScreen({
    super.key,
    this.patient,
    this.explanation,
    this.driver,
    this.result,
  });
  @override
  State<XaiDetailScreen> createState() => _XaiDetailScreenState();
}

class _XaiDetailScreenState extends State<XaiDetailScreen> {
  late final Future<Map<String, dynamic>> _future;
  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    if (widget.explanation != null) return widget.explanation!;
    final p = widget.patient;
    if (p == null) {
      throw StateError(
        'A fitted-model prediction is required for this explanation.',
      );
    }
    final age =
        DateTime.now().toUtc().difference(p.birthDateTime.toUtc()).inSeconds /
        3600;
    final payload = ResearchModelInputs.payload(
      ResearchModelInputs.prefill(p, age),
      age,
    );
    return Map<String, dynamic>.from(
      (await apiClient.dio.post(
            '/api/v1/research/model/explain',
            data: payload,
          )).data
          as Map,
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Model explainability')),
    body: FutureBuilder<Map<String, dynamic>>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          return Padding(
            padding: const EdgeInsets.all(24),
            child: const Text(
              'Could not load the model explanation. Check the measurements and connection, then try again.',
              style: TextStyle(fontSize: 16, height: 1.6),
            ),
          );
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        if (snapshot.data!['shap'] is! Map ||
            snapshot.data!['probability'] is! num) {
          return const Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              'An explanation is unavailable for these measurements. Review missing values and input ranges, then request a new score.',
              style: TextStyle(fontSize: 16, height: 1.6),
            ),
          );
        }
        final d = snapshot.data!,
            shap = Map<String, dynamic>.from(d['shap'] as Map);
        final contributions = (d['contributions'] as List)
            .map((c) => Map<String, dynamic>.from(c as Map))
            .toList();
        return ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'SHAP explanation',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Research model score: ${ResearchModelInputs.formatProbability(d['probability'] as num)}',
            ),
            const SizedBox(height: 14),
            const Text(
              'These inputs explain the research model score. They do not establish a diagnosis or a treatment effect.',
            ),
            const SizedBox(height: 16),
            ShapWaterfall(
              baseline: (shap['baseline_probability'] as num).toDouble(),
              prediction: (d['probability'] as num).toDouble(),
              contributions: contributions,
            ),
            const SizedBox(height: 16),
            const Text(
              'Input contributions',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
            ),
            for (final c in contributions)
              Card(
                child: ListTile(
                  title: Text(c['feature'].toString()),
                  subtitle: Text('Recorded model input: ${c['value']}'),
                  trailing: Text(
                    '${(c['contribution'] as num) >= 0 ? '+' : ''}${((c['contribution'] as num) * 100).toStringAsFixed(2)} pp',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: (c['contribution'] as num) >= 0
                          ? Colors.teal
                          : Colors.blueGrey,
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 12),
            const Text(
              'Positive contributions raise the score; negative contributions lower it. Values are percentage points.',
              style: TextStyle(height: 1.6),
            ),
          ],
        );
      },
    ),
  );
}
