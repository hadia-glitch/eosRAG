/// Exact de-identified research input contract. Unknowns remain null.
class LongitudinalInputs {
  static const version = 'pic-longitudinal-v1';
  static const measurements = {
    'neonatal_temperature',
    'heart_rate',
    'respiratory_rate',
    'spo2',
    'pulse_rate',
    'diastolic_pressure',
    'systolic_pressure',
    'measured_weight_kg',
  };
  static const contextFields = {
    'gestational_age_weeks',
    'birth_weight_kg',
    'maternal_age',
    'maternal_temperature',
    'rom_hours',
    'prom',
    'gbs_positive',
    'adequate_intrapartum_antibiotics',
    'clinical_chorioamnionitis',
    'maternal_infection',
    'cesarean',
    'apgar_1min',
    'apgar_5min',
    'resuscitation_needed',
    'fever',
    'hypothermia',
    'respiratory_distress',
    'poor_feeding',
    'lethargy',
    'jaundice',
  };

  static Map<String, dynamic> payload({
    required double ageHours,
    required List<Map<String, dynamic>> observations,
    required Map<String, dynamic> context,
    String? sex,
  }) {
    if (!ageHours.isFinite || ageHours < 0 || ageHours >= 72) {
      throw ArgumentError('Assessment age must be between 0 and 72 hours.');
    }
    if (context.keys.toSet().difference(contextFields).isNotEmpty ||
        contextFields.difference(context.keys.toSet()).isNotEmpty) {
      throw ArgumentError('Context fields do not match the model contract.');
    }
    if (observations.isEmpty || observations.length > 2000) {
      throw ArgumentError('Record between 1 and 2000 timed measurements.');
    }
    final seen = <String>{};
    for (final row in observations) {
      if (row.keys.toSet().difference({
            'field',
            'value',
            'age_hours',
            'available_age_hours',
          }).isNotEmpty ||
          row.length != 4 ||
          !measurements.contains(row['field'])) {
        throw ArgumentError('Unsupported measurement or identifying field.');
      }
      for (final key in ['value', 'age_hours', 'available_age_hours']) {
        if (row[key] is! num || !(row[key] as num).isFinite) {
          throw ArgumentError('Measurements and times must be finite numbers.');
        }
      }
      final time = (row['age_hours'] as num).toDouble();
      final known = (row['available_age_hours'] as num).toDouble();
      if (time < 0 || known < time || known > ageHours) {
        throw ArgumentError('Measurements must be known by assessment time.');
      }
      if (!seen.add('${row['field']}:$time')) {
        throw ArgumentError(
          'Reconcile duplicate measurements at the same time.',
        );
      }
    }
    for (final value in context.values) {
      if (value != null &&
          value is! bool &&
          (value is! num || !value.isFinite)) {
        throw ArgumentError(
          'Only measurements, booleans and unknowns are allowed.',
        );
      }
    }
    if (sex != null && !{'M', 'F'}.contains(sex)) {
      throw ArgumentError('Unsupported sex category.');
    }
    return {
      'sequence': {
        'input_contract_version': version,
        'purpose': 'research',
        'age_hours': ageHours,
        'sex': sex,
        'observations': [
          for (final row in observations) Map<String, dynamic>.from(row),
        ],
      },
      'context': Map<String, dynamic>.from(context),
    };
  }
}
