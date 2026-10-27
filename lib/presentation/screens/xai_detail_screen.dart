import 'package:flutter/material.dart';
import '../../domain/eoscal_calculator.dart';
import '../../data/api/api_client.dart';
import '../../data/research_model_inputs.dart';

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
            child: Text('No model explanation is available: ${snapshot.error}'),
          );
        }
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
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
              'Actual Kernel SHAP',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Model: ${d['model_version']}\nSupplied-label prediction: ${ResearchModelInputs.formatProbability(d['probability'] as num)}\nBaseline probability: ${((shap['baseline_probability'] as num) * 100).toStringAsFixed(2)}%',
            ),
            const SizedBox(height: 14),
            const Text(
              'Contributions change the research-model probability relative to its fit reference. They do not prove causation or prescribe treatment.',
            ),
            const SizedBox(height: 16),
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
            Text(
              'Additivity error: ${shap['additivity_error']}\nCoalition samples: ${shap['nsamples']}\n${shap['reference']}',
            ),
          ],
        );
      },
    ),
  );
}
