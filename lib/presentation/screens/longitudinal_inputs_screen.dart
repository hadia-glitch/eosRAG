import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import '../../data/api/api_client.dart';
import '../../data/longitudinal_inputs.dart';

/// Explicitly reviewed timing and unknowns; no clinical risk score is fabricated.
class LongitudinalInputsScreen extends StatefulWidget {
  final Future<Map<String, dynamic>> Function()? loadContract;
  final Future<Map<String, dynamic>> Function(Map<String, dynamic>)?
  previewInputs;
  const LongitudinalInputsScreen({
    super.key,
    this.loadContract,
    this.previewInputs,
  });
  @override
  State<LongitudinalInputsScreen> createState() =>
      _LongitudinalInputsScreenState();
}

class _LongitudinalInputsScreenState extends State<LongitudinalInputsScreen> {
  Map<String, dynamic>? _contract, _result;
  String? _error, _sex;
  bool _busy = false;
  int _revision = 0;
  final _age = TextEditingController();
  final _time = TextEditingController();
  final _known = TextEditingController();
  final _value = TextEditingController();
  final _numbers = <String, TextEditingController>{};
  final _context = <String, dynamic>{
    for (final k in LongitudinalInputs.contextFields) k: null,
  };
  final _observations = <Map<String, dynamic>>[];
  String _field = 'heart_rate';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final data = widget.loadContract != null
          ? await widget.loadContract!()
          : Map<String, dynamic>.from(
              (await apiClient.dio.get(
                '/api/v1/research/longitudinal/contract',
              )).data,
            );
      if (!mounted) return;
      if (data['input_contract_version'] != LongitudinalInputs.version) {
        throw StateError('The server input contract changed. Update the app.');
      }
      final contexts = (data['context_fields'] as List)
          .map((e) => e['key'] as String)
          .toSet();
      final measurements = (data['sequence_fields'] as List)
          .map((e) => e['key'] as String)
          .toSet();
      if (contexts.difference(LongitudinalInputs.contextFields).isNotEmpty ||
          LongitudinalInputs.contextFields.difference(contexts).isNotEmpty ||
          measurements.difference(LongitudinalInputs.measurements).isNotEmpty ||
          LongitudinalInputs.measurements.difference(measurements).isNotEmpty) {
        throw StateError('The app and server fields do not match.');
      }
      for (final f in data['context_fields'] as List) {
        if (f['unit'] != 'boolean') {
          _numbers[f['key']] = TextEditingController();
        }
      }
      if (mounted) {
        setState(() {
          _contract = data;
          _error = null;
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Unable to load the input contract. Check the connection and sign-in, then retry.',
        );
      }
    }
  }

  @override
  void dispose() {
    for (final c in [_age, _time, _known, _value, ..._numbers.values]) {
      c.dispose();
    }
    super.dispose();
  }

  Map<dynamic, dynamic> get _measurement =>
      (_contract!['sequence_fields'] as List).firstWhere(
        (f) => f['key'] == _field,
      );

  void _add() {
    try {
      final age = double.parse(_age.text);
      final time = double.parse(_time.text);
      final known = double.parse(_known.text);
      final value = double.parse(_value.text);
      final meta = _measurement;
      if (!value.isFinite ||
          value < (meta['min'] as num) ||
          value > (meta['max'] as num)) {
        throw ArgumentError('Check the measurement unit and accepted range.');
      }
      final rows = [
        ..._observations,
        {
          'field': _field,
          'value': value,
          'age_hours': time,
          'available_age_hours': known,
        },
      ];
      LongitudinalInputs.payload(
        ageHours: age,
        observations: rows,
        context: _context,
        sex: _sex,
      );
      rows.sort(
        (a, b) => (a['age_hours'] as num).compareTo(b['age_hours'] as num),
      );
      setState(() {
        _observations
          ..clear()
          ..addAll(rows);
        _result = null;
        _revision++;
        _error = null;
      });
      _value.clear();
    } catch (e) {
      setState(
        () => _error =
            'Check assessment age, measurement age, availability age and value. $e',
      );
    }
  }

  Future<void> _preview() async {
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    final requestRevision = _revision;
    try {
      final values = {..._context};
      for (final e in _numbers.entries) {
        values[e.key] = e.value.text.trim().isEmpty
            ? null
            : double.parse(e.value.text);
      }
      final payload = LongitudinalInputs.payload(
        ageHours: double.parse(_age.text),
        observations: _observations,
        context: values,
        sex: _sex,
      );
      final response = widget.previewInputs != null
          ? await widget.previewInputs!(payload)
          : Map<String, dynamic>.from(
              (await apiClient.dio.post(
                (_contract?['prediction_endpoint'] as String?) ??
                    '/api/v1/research/longitudinal/preview',
                data: payload,
              )).data,
            );
      if (mounted) {
        setState(() {
          if (requestRevision == _revision) {
            _result = response;
          } else {
            _error =
                'Inputs changed during the request. Review the updated history again.';
          }
        });
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'Input review could not complete. Check units, ranges, timing and sign-in; no prediction has been substituted.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _numeric(
    TextEditingController controller,
    String label, {
    String? helper,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextField(
      key: ValueKey(label),
      controller: controller,
      onChanged: (_) {
        setState(() {
          _revision++;
          _result = null;
        });
      },
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      textInputAction: TextInputAction.done,
      onSubmitted: (_) => FocusScope.of(context).unfocus(),
      decoration: InputDecoration(
        labelText: label,
        helperText: helper,
        helperMaxLines: 3,
        border: const OutlineInputBorder(),
      ),
    ),
  );

  Widget _section(String title, List<Widget> content) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 14),
          ...content,
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Longitudinal research inputs')),
    body: _contract == null
        ? Center(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(_error ?? 'Loading input contract…'),
                TextButton(onPressed: _load, child: const Text('Retry')),
              ],
            ),
          )
        : ListView(
            padding: const EdgeInsets.all(12),
            children: [
              _section(
                _contract?['selected_model'] == 'pic'
                    ? 'PIC research model'
                    : 'Research model — prediction withheld',
                [
                  const Text(
                    'The new real-data candidate does not meet the quality target. This screen reviews recorded history and input completeness; it does not provide a clinical EOS probability.',
                  ),
                  const SizedBox(height: 10),
                  const Text(
                    'Maternal and perinatal factors are retained as context. Synthetic maternal modelling is separate from the real neonatal cohort. Unknown does not mean normal.',
                  ),
                ],
              ),
              _section('1. Assessment timing', [
                _numeric(
                  _age,
                  'Age at assessment (hours)',
                  helper: 'At least 0 and below 72 hours.',
                ),
                DropdownButtonFormField<String>(
                  initialValue: _sex ?? 'unknown',
                  decoration: const InputDecoration(labelText: 'Sex'),
                  items: const [
                    DropdownMenuItem(value: 'unknown', child: Text('Unknown')),
                    DropdownMenuItem(value: 'F', child: Text('Female')),
                    DropdownMenuItem(value: 'M', child: Text('Male')),
                  ],
                  onChanged: (v) => setState(() {
                    _sex = v == 'unknown' ? null : v;
                    _revision++;
                    _result = null;
                  }),
                ),
              ]),
              _section('2. Recorded observations over time', [
                const Text(
                  'Add earlier and current measurements. Availability age is when the measurement was documented and known. Old observations keep their original time.',
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<String>(
                  initialValue: _field,
                  decoration: const InputDecoration(labelText: 'Measurement'),
                  items: [
                    for (final f in _contract!['sequence_fields'] as List)
                      DropdownMenuItem(
                        value: f['key'] as String,
                        child: Text('${f['label']} (${f['unit']})'),
                      ),
                  ],
                  onChanged: (v) => setState(() {
                    _field = v!;
                    _revision++;
                    _result = null;
                  }),
                ),
                const SizedBox(height: 12),
                _numeric(_time, 'Age when measured (hours)'),
                _numeric(_known, 'Age when available (hours)'),
                _numeric(_value, 'Value (${_measurement['unit']})'),
                OutlinedButton.icon(
                  onPressed: _add,
                  icon: const Icon(Icons.add),
                  label: const Text('Add timed measurement'),
                ),
                for (final row in _observations)
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    title: Text(
                      '${(_contract!['sequence_fields'] as List).firstWhere((f) => f['key'] == row['field'])['label']}: ${row['value']}',
                    ),
                    subtitle: Text(
                      'Measured ${row['age_hours']} h · known ${row['available_age_hours']} h',
                    ),
                    trailing: IconButton(
                      tooltip: 'Remove measurement',
                      icon: const Icon(Icons.delete_outline),
                      onPressed: () => setState(() {
                        _observations.remove(row);
                        _revision++;
                        _result = null;
                      }),
                    ),
                  ),
                if (_observations.where((r) => r['field'] == _field).length >=
                    2) ...[
                  const SizedBox(height: 8),
                  Text(
                    'Recorded ${_measurement['label']} (${_measurement['unit']})',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  const Text(
                    'Horizontal axis: postnatal age in hours. Points show recorded values.',
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 190,
                    child: LineChart(
                      LineChartData(
                        lineBarsData: [
                          LineChartBarData(
                            isCurved: false,
                            color: Colors.teal,
                            spots: [
                              for (final r in _observations.where(
                                (r) => r['field'] == _field,
                              ))
                                FlSpot(
                                  (r['age_hours'] as num).toDouble(),
                                  (r['value'] as num).toDouble(),
                                ),
                            ],
                          ),
                        ],
                        titlesData: const FlTitlesData(
                          topTitles: AxisTitles(
                            sideTitles: SideTitles(showTitles: false),
                          ),
                          rightTitles: AxisTitles(
                            sideTitles: SideTitles(showTitles: false),
                          ),
                        ),
                      ),
                    ),
                  ),
                ],
              ]),
              _section('3. Maternal, perinatal and clinical context', [
                const Text(
                  'Leave unrecorded values unknown. These fields are not learned maternal effects in the PIC model.',
                ),
                const SizedBox(height: 12),
                for (final f in _contract!['context_fields'] as List)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: f['unit'] == 'boolean'
                        ? DropdownButtonFormField<String>(
                            initialValue: 'unknown',
                            isExpanded: true,
                            decoration: InputDecoration(
                              labelText: f['label'] as String,
                              helperText: f['use'] as String,
                              helperMaxLines: 3,
                            ),
                            items: const [
                              DropdownMenuItem(
                                value: 'unknown',
                                child: Text('Unknown / not recorded'),
                              ),
                              DropdownMenuItem(
                                value: 'yes',
                                child: Text('Yes'),
                              ),
                              DropdownMenuItem(value: 'no', child: Text('No')),
                            ],
                            onChanged: (v) => setState(() {
                              _context[f['key']] = v == 'unknown'
                                  ? null
                                  : v == 'yes';
                              _revision++;
                              _result = null;
                            }),
                          )
                        : _numeric(
                            _numbers[f['key']]!,
                            '${f['label']} (${f['unit']})',
                            helper: f['use'] as String,
                          ),
                  ),
              ]),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.all(12),
                  child: Text(
                    _error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ),
              FilledButton.icon(
                onPressed: _busy ? null : _preview,
                icon: const Icon(Icons.fact_check_outlined),
                label: Text(
                  _busy
                      ? 'Reviewing…'
                      : _contract?['selected_model'] == 'pic'
                      ? 'Calculate research score and review trends'
                      : 'Review history and inputs',
                ),
              ),
              if (_result != null)
                _section('4. Recorded trend review', [
                  if (_result!['research_score'] != null) ...[
                    Text(
                      '${((_result!['research_score'] as num) * 100).toStringAsFixed(2)}%',
                      style: const TextStyle(
                        fontSize: 28,
                        fontWeight: FontWeight.bold,
                        color: Colors.teal,
                      ),
                    ),
                    const Text(
                      'Uncalibrated PIC research score',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                  ],
                  Text(
                    _result!['notice'] as String,
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                  const SizedBox(height: 12),
                  if (_result!['contributions'] != null) ...[
                    const Text(
                      'Model explanation · log-odds contributions',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    for (final c in (_result!['contributions'] as List).take(8))
                      Text(
                        '${c['feature']}: ${(c['contribution'] as num).toStringAsFixed(3)}',
                        style: const TextStyle(height: 1.6),
                      ),
                    const SizedBox(height: 12),
                  ],
                  for (final e in (_result!['trends'] as Map).entries)
                    if ((e.value as Map)['count'] > 0)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: Text(
                          '${(_contract!['sequence_fields'] as List).firstWhere((f) => f['key'] == e.key)['label']}\n'
                          '${e.value['count']} recorded measurements · latest recent value: ${e.value['last'] ?? 'not recorded'}\n'
                          'Change: ${e.value['delta'] ?? 'requires two measurements'} · slope per hour: ${e.value['slope_per_hour'] ?? 'unavailable'}',
                        ),
                      ),
                ]),
            ],
          ),
  );
}
