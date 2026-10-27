import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:intl/intl.dart';
import '../../domain/eoscal_calculator.dart';
import '../../data/auth_service.dart';
import '../../data/supabase_config.dart';
import '../../data/deidentify.dart';

/// Actual serial observations; missing values and unobserved times are not
/// drawn as zero values or fabricated risk scores.
class PatientTimelineScreen extends StatefulWidget {
  final PatientParameters patient;
  final EoscalResult result;
  const PatientTimelineScreen({
    super.key,
    required this.patient,
    required this.result,
  });
  @override
  State<PatientTimelineScreen> createState() => _PatientTimelineScreenState();
}

class _PatientTimelineScreenState extends State<PatientTimelineScreen> {
  List<Map<String, dynamic>> _rows = [];
  bool _loading = true;
  String? _notice;
  String _measure = 'crp_level';
  static const _labels = {
    'crp_level': 'CRP (mg/L)',
    'neonatal_temperature': 'Temperature (C)',
    'creatinine_mg_dl': 'Creatinine (mg/dL)',
    'platelet_count': 'Platelets (cells/mm3)',
    'wbc_count': 'WBC (cells/mm3)',
    'pct_level': 'Procalcitonin (ng/mL)',
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    if (mounted) setState(() => _loading = true);
    List<Map<String, dynamic>> records = [];
    String? notice;
    if (SupabaseConfig.isConfigured && AuthService.instance.isSignedIn) {
      try {
        final data = await AuthService.instance.client
            .from('clinical_assessments')
            .select(
              'created_at,event_type,maternal_data,neonatal_data,lab_data',
            )
            .eq('encounter_id', widget.patient.id)
            .order('created_at', ascending: false)
            .limit(200);
        records = data
            .map((r) => Map<String, dynamic>.from(r))
            .toList()
            .reversed
            .toList();
        if (records.length == 200) {
          notice = 'Showing the latest 200 assessments.';
        }
      } catch (_) {
        notice =
            'Stored history could not be loaded. Showing the current local snapshot only.';
      }
    } else {
      notice =
          'Sign in to load stored history. Showing the current local snapshot only.';
    }
    if (records.isEmpty) {
      notice ??=
          'No stored serial assessments. Showing the current local snapshot only.';
      records = [
        {
          'created_at': DateTime.now().toUtc().toIso8601String(),
          'event_type': 'current local snapshot',
          'snapshot': DeidentifiedPatient.fromPatient(widget.patient).toJson(),
        },
      ];
    }
    if (!mounted) return;
    setState(() {
      _rows = records;
      _notice = notice;
      _loading = false;
    });
  }

  Map<String, dynamic> _values(Map<String, dynamic> row) {
    final values = <String, dynamic>{};
    for (final key in [
      'snapshot',
      'maternal_data',
      'neonatal_data',
      'lab_data',
    ]) {
      values.addAll(Map<String, dynamic>.from(row[key] as Map? ?? {}));
    }
    return values;
  }

  List<FlSpot> _spots() {
    final out = <FlSpot>[];
    for (final row in _rows) {
      final time = DateTime.tryParse(row['created_at'] as String? ?? '');
      final value = _values(row)[_measure];
      if (time == null || value is! num || !value.isFinite) continue;
      final age =
          time
              .toUtc()
              .difference(widget.patient.birthDateTime.toUtc())
              .inSeconds /
          3600;
      if (age < 0) continue;
      out.add(FlSpot(age, value.toDouble()));
    }
    out.sort((a, b) => a.x.compareTo(b.x));
    return out;
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    final spots = _spots();
    final elapsed = spots.length >= 2
        ? spots.last.x - spots[spots.length - 2].x
        : null;
    final delta = spots.length >= 2
        ? spots.last.y - spots[spots.length - 2].y
        : null;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            'Measured clinical history',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          if (_notice != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Text(_notice!),
            ),
          const Text(
            'Changes in individual measurements are not an EOS diagnosis or a validated risk trend.',
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _measure,
            decoration: const InputDecoration(labelText: 'Measurement'),
            items: _labels.entries
                .map(
                  (e) => DropdownMenuItem(value: e.key, child: Text(e.value)),
                )
                .toList(),
            onChanged: (v) {
              if (v != null) setState(() => _measure = v);
            },
          ),
          const SizedBox(height: 12),
          if (spots.isEmpty)
            const Padding(
              padding: EdgeInsets.all(24),
              child: Text('No recorded values for this measurement.'),
            )
          else ...[
            Text(
              '${spots.length} observed values${delta == null ? '' : '; last change ${delta >= 0 ? '+' : ''}${delta.toStringAsFixed(2)} over ${elapsed!.toStringAsFixed(1)} h'}',
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 240,
              child: Padding(
                padding: const EdgeInsets.only(right: 16, top: 8),
                child: LineChart(
                  LineChartData(
                    minX: spots.first.x,
                    maxX: spots.last.x > spots.first.x
                        ? spots.last.x
                        : spots.first.x + 1,
                    lineBarsData: [
                      LineChartBarData(
                        spots: spots,
                        isCurved: false,
                        color: Colors.teal,
                        barWidth: spots.length > 1 ? 2 : 0,
                        dotData: const FlDotData(show: true),
                      ),
                    ],
                    titlesData: const FlTitlesData(
                      topTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      rightTitles: AxisTitles(
                        sideTitles: SideTitles(showTitles: false),
                      ),
                      bottomTitles: AxisTitles(
                        axisNameWidget: Text('Age since birth (hours)'),
                        sideTitles: SideTitles(
                          showTitles: true,
                          reservedSize: 24,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ],
          const SizedBox(height: 24),
          ..._rows.reversed.map((row) {
            final time = DateTime.tryParse(row['created_at'] as String? ?? '');
            final values = _values(
              row,
            ).entries.where((e) => e.value != null).toList();
            return Card(
              child: ExpansionTile(
                title: Text(
                  time == null
                      ? 'Time unknown'
                      : DateFormat('dd MMM yyyy HH:mm').format(time.toLocal()),
                ),
                subtitle: Text(row['event_type'] as String? ?? 'Assessment'),
                children: values
                    .map(
                      (e) => ListTile(
                        dense: true,
                        title: Text(
                          _labels[e.key] ?? e.key.replaceAll('_', ' '),
                        ),
                        trailing: Text('${e.value}'),
                      ),
                    )
                    .toList(),
              ),
            );
          }),
        ],
      ),
    );
  }
}
