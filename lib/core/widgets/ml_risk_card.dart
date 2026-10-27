import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import '../../data/api/api_client.dart';
import '../../data/auth_service.dart';
import '../../data/deidentify.dart';
import '../../data/supabase_config.dart';
import '../../domain/eoscal_calculator.dart';
import 'research_model_card.dart';

/// Asynchronous model result with explicit unavailable/abstained states.
/// No local point score or invented probability substitutes for inference.
class MlRiskCard extends StatefulWidget {
  final PatientParameters patient;
  const MlRiskCard({super.key, required this.patient});
  @override
  State<MlRiskCard> createState() => _MlRiskCardState();
}

class _MlRiskCardState extends State<MlRiskCard> {
  late Future<Map<String, dynamic>> _future;
  bool _usesResearchModel = false;
  static const _predictors = {
    'gestational_age_weeks',
    'birth_weight_g',
    'maternal_temperature',
    'rom_hours',
    'neonatal_temperature',
    'heart_rate',
    'respiratory_rate',
    'spo2',
    'crp_level',
    'wbc_count',
    'platelet_count',
    'pct_level',
    'it_ratio',
    'creatinine_mg_dl',
    'urine_output_ml_kg_hr',
    'apgar_5_min',
    'gbs_positive',
    'adequate_intrapartum_antibiotics',
    'clinical_chorioamnionitis',
    'poor_perfusion',
    'respiratory_distress',
    'oxygen_need',
    'neurological_status',
  };

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  @override
  void didUpdateWidget(covariant MlRiskCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.patient.id != widget.patient.id ||
        (!_usesResearchModel &&
            !identical(oldWidget.patient, widget.patient))) {
      _future = _load();
    }
  }

  Map<String, dynamic> _values(Map<String, dynamic> raw) => Map.fromEntries(
    raw.entries.where((e) => _predictors.contains(e.key) && e.value != null),
  );

  Future<Map<String, dynamic>> _load() async {
    final age =
        DateTime.now()
            .toUtc()
            .difference(widget.patient.birthDateTime.toUtc())
            .inSeconds /
        3600;
    if (age < 0 || age > 72) {
      return {
        'status': 'abstained',
        'warnings': [
          'Outside this EOS model workflow (0-72 hours). Seek neonatal clinical assessment.',
        ],
      };
    }
    final status = await apiClient.dio.get('/api/v1/models/status');
    final metadata = Map<String, dynamic>.from(status.data as Map);
    if (metadata['available'] != true) {
      final research = metadata['research_model'] as Map?;
      if (research?['available'] == true) {
        _usesResearchModel = true;
        return {
          'status': 'research_available',
          'research_model': Map<String, dynamic>.from(research!),
        };
      }
      return {
        'status': 'unavailable',
        'warnings': [
          metadata['reason'] ?? 'No trained EOS model has been installed.',
        ],
      };
    }
    final history = <Map<String, dynamic>>[];
    if (SupabaseConfig.isConfigured && AuthService.instance.isSignedIn) {
      final rows = await AuthService.instance.client
          .from('clinical_assessments')
          .select('created_at,maternal_data,neonatal_data,lab_data')
          .eq('encounter_id', widget.patient.id)
          .order('created_at', ascending: false)
          .limit(200);
      final seenTimes = <double>{};
      for (final row in rows) {
        final time = DateTime.tryParse(row['created_at'] as String? ?? '');
        if (time == null) continue;
        final hours =
            time
                .toUtc()
                .difference(widget.patient.birthDateTime.toUtc())
                .inSeconds /
            3600;
        if (hours < 0 || hours >= age || !seenTimes.add(hours)) continue;
        final raw = <String, dynamic>{};
        for (final key in ['maternal_data', 'neonatal_data', 'lab_data']) {
          raw.addAll(Map<String, dynamic>.from(row[key] as Map? ?? {}));
        }
        history.add({'age_hours': hours, 'values': _values(raw)});
      }
    }
    final response = await apiClient.dio.post(
      '/api/v1/risk/predict',
      data: {
        'current': {
          'age_hours': age,
          'values': _values(
            DeidentifiedPatient.fromPatient(widget.patient).toJson(),
          ),
        },
        'history': history,
        'purpose': 'research',
      },
    );
    return Map<String, dynamic>.from(response.data as Map);
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snapshot) {
            final data = snapshot.data;
            if (data?['status'] == 'research_available') {
              return ResearchModelCard(
                key: ValueKey(widget.patient.id),
                patient: widget.patient,
                metadata: Map<String, dynamic>.from(
                  data!['research_model'] as Map,
                ),
              );
            }
            final predicted = data?['status'] == 'predicted';
            final warnings = (data?['warnings'] as List? ?? [])
                .map((e) => e.toString())
                .toList();
            if (snapshot.hasError) {
              final error = snapshot.error;
              warnings.add(
                error is DioException && error.response?.statusCode == 401
                    ? 'Sign in to request an EOS assessment.'
                    : 'Model assessment unavailable. Retry or contact the administrator.',
              );
            }
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'EOS model assessment',
                  style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 12),
                if (snapshot.connectionState == ConnectionState.waiting) ...[
                  const LinearProgressIndicator(),
                  const SizedBox(height: 8),
                  const Text(
                    'Checking model availability and patient scope...',
                  ),
                ] else if (predicted) ...[
                  Text(
                    '${(data!['probability_per_1000'] as num).toStringAsFixed(2)} per 1,000',
                    style: const TextStyle(fontSize: 28),
                  ),
                  Text('Research estimate - ${data['model_version']}'),
                  Text(
                    'Missing predictors: ${((data['missing_fraction'] as num) * 100).round()}%',
                  ),
                  const SizedBox(height: 12),
                  Text('Feature contributions: ${data['contribution_method']}'),
                  ...((data['contributions'] as List?) ?? [])
                      .take(6)
                      .map(
                        (c) => Text(
                          '${c['feature']}: ${(c['contribution'] as num).toStringAsFixed(3)}',
                        ),
                      ),
                ] else
                  const Text(
                    'Risk not assessed',
                    style: TextStyle(fontSize: 24, fontWeight: FontWeight.w600),
                  ),
                ...warnings.map(
                  (warning) => Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(warning),
                  ),
                ),
                const SizedBox(height: 12),
                const Text(
                  'An unavailable estimate does not mean low risk. Use clinical assessment and your approved neonatal pathway. Model output does not authorize treatment.',
                ),
                TextButton.icon(
                  onPressed: () => setState(() => _future = _load()),
                  icon: const Icon(Icons.refresh),
                  label: const Text('Reassess'),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
