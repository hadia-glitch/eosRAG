import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'dart:convert';
import '../../data/api/api_client.dart';
import '../../data/research_model_inputs.dart';
import '../../domain/eoscal_calculator.dart';
import '../../presentation/patient_state.dart';

class ResearchModelCard extends ConsumerStatefulWidget {
  final PatientParameters patient;
  final Map<String, dynamic> metadata;
  const ResearchModelCard({
    super.key,
    required this.patient,
    required this.metadata,
  });
  @override
  ConsumerState<ResearchModelCard> createState() => _ResearchModelCardState();
}

class _ResearchModelCardState extends ConsumerState<ResearchModelCard> {
  Map<String, dynamic>? _result;
  String? _error;
  bool _busy = false;
  Map<String, dynamic>? _lastPayload;

  String _inputFingerprint(PatientParameters p) => jsonEncode([
    p.gestationalAgeWeeks,
    p.birthWeightGrams,
    p.birthDateTime.toIso8601String(),
    p.neonatalTemperature,
    p.apgar5Min,
    p.deliveryMode,
    p.assessmentRecordedAt?.toIso8601String(),
    p.researchInputsReviewedAt?.toIso8601String(),
    for (final name in ResearchModelInputs.names) p.researchModelInputs[name],
  ]);

  @override
  void didUpdateWidget(covariant ResearchModelCard oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_busy &&
        _inputFingerprint(oldWidget.patient) !=
            _inputFingerprint(widget.patient)) {
      _result = null;
      _error = null;
      _lastPayload = null;
    }
  }

  Future<void> _reviewAndPredict() async {
    final assessmentAt = DateTime.now().toUtc();
    final age =
        assessmentAt
            .difference(widget.patient.birthDateTime.toUtc())
            .inSeconds /
        3600;
    if (age < 0 || age >= 72) {
      setState(
        () => _error =
            'Outside this model age window: assessment age must be below 72 hours.',
      );
      return;
    }
    final rawFields = widget.metadata['input_contract'] as List? ?? [];
    final fields = rawFields
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
    final keys = fields.map((e) => e['name'] as String).toSet();
    if (widget.metadata['input_contract_version'] !=
            ResearchModelInputs.version ||
        keys.difference(ResearchModelInputs.names).isNotEmpty ||
        ResearchModelInputs.names.difference(keys).isNotEmpty) {
      setState(
        () => _error =
            'Model input contract changed. Update the app before predicting.',
      );
      return;
    }
    final values = await showDialog<Map<String, dynamic>>(
      context: context,
      barrierDismissible: false,
      builder: (_) => _ModelInputDialog(
        fields: fields,
        initial: ResearchModelInputs.prefill(widget.patient, age),
        age: age,
        maxMissing:
            (widget.metadata['max_missing_predictors'] as num?)?.toInt() ?? 0,
        lastReview: widget.patient.researchInputsReviewedAt,
      ),
    );
    if (values == null || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final patient = widget.patient.copyWith(
        researchModelInputs: Map.unmodifiable(values),
        assessmentRecordedAt: assessmentAt,
        researchInputsReviewedAt: assessmentAt,
        gestationalAgeWeeks: (values['Gestational_Age'] as num).toDouble(),
        birthWeightGrams: (values['Birth_Weight'] as num).toDouble() * 1000,
        apgar5Min: (values['Apgar'] as num).toInt(),
        neonatalTemperature: (values['Temp'] as num?)?.toDouble(),
        deliveryMode: values['Delivery_Mode'] == 'Cesarean'
            ? 'Caesarean'
            : 'Vaginal',
      );
      // Persist the complete input set, including explicit unknowns. The server
      // receives only allowlisted research measurements, never patient identity.
      await ref.read(patientsProvider.notifier).updatePatient(patient);
      _lastPayload = ResearchModelInputs.payload(values, age);
      final response = await apiClient.dio.post(
        '/api/v1/research/model/predict',
        data: _lastPayload,
      );
      if (mounted) {
        setState(
          () => _result = Map<String, dynamic>.from(response.data as Map),
        );
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          if (error is DioException) {
            final status = error.response?.statusCode;
            _error = status == 401
                ? 'Sign in to request a model prediction.'
                : status == 422
                ? 'Input validation failed. Review the measurements and model units.'
                : 'Model service unavailable. Check the backend connection and retry.';
          } else {
            _error =
                'The reviewed input set could not be saved or evaluated. Retry after checking the connection.';
          }
        });
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _explainWithShap() async {
    if (_lastPayload == null) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final response = await apiClient.dio.post(
        '/api/v1/research/model/explain',
        data: _lastPayload,
      );
      if (mounted) {
        setState(
          () => _result = Map<String, dynamic>.from(response.data as Map),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'SHAP explanation unavailable. The existing prediction is retained.',
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final result = _result;
    final predicted = result?['status'] == 'predicted';
    final contributions = (result?['contributions'] as List?) ?? [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Trained sepsis-label model',
          style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 6),
        const Chip(
          label: Text('RESEARCH ONLY - CLINICAL EOS RISK NOT VALIDATED'),
        ),
        Text(widget.metadata['version'] as String? ?? ''),
        const SizedBox(height: 10),
        if (predicted) ...[
          Text(
            ResearchModelInputs.formatProbability(
              result!['probability'] as num,
            ),
            style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
          ),
          const Text(
            'Probability of the supplied dataset label, not clinical EOS risk.',
          ),
          if (result['probability_details'] is Map) ...[
            const SizedBox(height: 8),
            Text(
              'Raw model score: ${((result['probability_details']['raw_model_score'] as num) * 100).toStringAsFixed(4)}%. '
              'The displayed dataset score follows a fitted calibration transform.',
            ),
            if (result['probability_details']['extreme_score'] == true)
              const Text(
                'Extreme dataset score: numerical saturation does not establish diagnostic certainty.',
                style: TextStyle(fontWeight: FontWeight.bold),
              ),
          ],
          if (_lastPayload != null)
            Text(
              'Reviewed assessment age: ${(_lastPayload!['age_hours'] as num).toStringAsFixed(2)} hours. This result belongs to that assessment.',
            ),
          Text(
            'Unknown inputs: ${(result['missing_features'] as List).length} of 18. Imputation is shown below.',
          ),
          const SizedBox(height: 10),
          Text('Input effects: ${result['contribution_method']}'),
          ...contributions
              .take(6)
              .map(
                (c) => Text(
                  '${c['feature']}: ${((c['contribution'] as num) * 100).toStringAsFixed(2)} percentage points',
                ),
              ),
        ] else if (result != null)
          const Text(
            'Prediction withheld: inputs are outside model support.',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
        ...((result?['warnings'] as List?) ?? []).map(
          (w) => Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(w.toString()),
          ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        const SizedBox(height: 10),
        Text(
          'Development-matched missingness limit: ${widget.metadata['max_missing_predictors']} unknown measurements.',
        ),
        const Text(
          'Review all 18 model fields before running. Undocumented dataset units are kept separate from clinical lab units. No antibiotic decision is generated.',
        ),
        const SizedBox(height: 10),
        if (_busy) const LinearProgressIndicator(),
        FilledButton.icon(
          onPressed: _busy ? null : _reviewAndPredict,
          icon: const Icon(Icons.fact_check_outlined),
          label: const Text('Review model inputs & predict'),
        ),
        if (predicted)
          OutlinedButton.icon(
            onPressed: _busy ? null : _explainWithShap,
            icon: const Icon(Icons.analytics_outlined),
            label: const Text('Explain with SHAP'),
          ),
      ],
    );
  }
}

class _ModelInputDialog extends StatefulWidget {
  final List<Map<String, dynamic>> fields;
  final Map<String, dynamic> initial;
  final double age;
  final int maxMissing;
  final DateTime? lastReview;
  const _ModelInputDialog({
    required this.fields,
    required this.initial,
    required this.age,
    required this.maxMissing,
    this.lastReview,
  });
  @override
  State<_ModelInputDialog> createState() => _ModelInputDialogState();
}

class _ModelInputDialogState extends State<_ModelInputDialog> {
  final _form = GlobalKey<FormState>();
  final _controllers = <String, TextEditingController>{};
  final _unknown = <String, bool>{};
  final _categories = <String, String?>{};
  bool _confirmed = false;
  String? _validationError;

  @override
  void initState() {
    super.initState();
    for (final f in widget.fields) {
      final name = f['name'] as String;
      final value = widget.initial[name];
      if (f['categories'] != null) {
        _categories[name] = value as String?;
      } else {
        _controllers[name] = TextEditingController(
          text: value?.toString() ?? '',
        );
      }
      _unknown[name] = value == null && f['required'] != true;
    }
  }

  @override
  void dispose() {
    for (final c in _controllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  void _submit() {
    if (!_confirmed || !_form.currentState!.validate()) return;
    final missing = _unknown.values.where((value) => value).length;
    if (missing > widget.maxMissing) {
      setState(
        () => _validationError =
            'This model supports at most ${widget.maxMissing} unknown measurements; $missing are marked unknown. Record documented measurements or cancel. Do not guess values.',
      );
      return;
    }
    final values = <String, dynamic>{};
    for (final f in widget.fields) {
      final name = f['name'] as String;
      values[name] = f['categories'] != null
          ? _categories[name]
          : _unknown[name] == true
          ? null
          : double.parse(_controllers[name]!.text.trim());
    }
    Navigator.pop(context, values);
  }

  @override
  Widget build(BuildContext context) => AlertDialog(
    title: const Text('Review trained-model inputs'),
    content: SizedBox(
      width: 560,
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Assessment age: ${widget.age.toStringAsFixed(2)} hours. Postnatal age uses completed days.',
              ),
              const SizedBox(height: 8),
              if (widget.lastReview != null)
                Text(
                  'Previously reviewed: ${widget.lastReview!.toLocal()}. Confirm measurements for this assessment; saved values are not new observations.',
                ),
              const Text(
                'Dataset laboratory units and numeric oxygen definition are undocumented. Do not substitute clinical laboratory values using guessed conversions. Leave unknown or enter values from a documented research source.',
              ),
              const SizedBox(height: 16),
              for (final f in widget.fields)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: _field(f),
                ),
              CheckboxListTile(
                value: _confirmed,
                contentPadding: EdgeInsets.zero,
                title: const Text(
                  'I reviewed each measurement, its units, and the fields marked unknown for this assessment.',
                ),
                onChanged: (v) => setState(() => _confirmed = v ?? false),
              ),
            ],
          ),
        ),
      ),
    ),
    actions: [
      if (_validationError != null)
        Text(_validationError!, style: const TextStyle(color: Colors.red)),
      TextButton(
        onPressed: () => Navigator.pop(context),
        child: const Text('Cancel'),
      ),
      FilledButton(
        onPressed: _confirmed ? _submit : null,
        child: const Text('Save inputs & predict'),
      ),
    ],
  );

  Widget _field(Map<String, dynamic> field) {
    final name = field['name'] as String;
    final label = '${field['label']} ($name)';
    if (field['categories'] != null) {
      return DropdownButtonFormField<String>(
        initialValue: _categories[name],
        isExpanded: true,
        decoration: InputDecoration(labelText: label),
        items: (field['categories'] as List)
            .map(
              (v) =>
                  DropdownMenuItem<String>(value: v as String, child: Text(v)),
            )
            .toList(),
        validator: (v) => v == null ? 'Record this required category' : null,
        onChanged: (v) => setState(() => _categories[name] = v),
      );
    }
    final unknown = _unknown[name] == true;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _controllers[name],
          enabled: !unknown,
          readOnly: field['read_only'] == true,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: label,
            helperText: field['unit'] as String,
            helperMaxLines: 2,
            hintText: 'Measured value',
          ),
          validator: (s) {
            if (unknown) return null;
            final value = double.tryParse(s?.trim() ?? '');
            if (value == null || !value.isFinite) {
              return 'Enter a number or mark unknown';
            }
            if (value < (field['minimum'] as num) ||
                value > (field['maximum'] as num)) {
              return 'Input range: ${field['minimum']} to ${field['maximum']}';
            }
            if (name == 'Apgar' && value != value.roundToDouble()) {
              return 'Enter an integer score';
            }
            final support = field['development_range'] as List?;
            if (support != null &&
                (value < (support[0] as num) || value > (support[1] as num))) {
              return 'Outside model development support (${support[0]} to ${support[1]}). This model cannot assess it.';
            }
            return null;
          },
        ),
        if (field['required'] != true)
          CheckboxListTile(
            contentPadding: EdgeInsets.zero,
            dense: true,
            value: unknown,
            title: const Text('Unknown / not measured'),
            onChanged: (v) => setState(() => _unknown[name] = v ?? true),
          ),
      ],
    );
  }
}
