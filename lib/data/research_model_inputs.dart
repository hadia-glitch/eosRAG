import '../domain/eoscal_calculator.dart';

/// Explicit allowlist shared with the installed supplied-label model contract.
/// This payload cannot contain a name, MRN, date, notes or arbitrary text.
class ResearchModelInputs {
  static String formatProbability(num probability) {
    if (probability > 0 && probability < 0.001) return '<0.1%';
    if (probability < 1 && probability > 0.999) return '>99.9%';
    return '${(probability * 100).toStringAsFixed(1)}%';
  }

  static const version = 'supplied-neonatal-input-v1';
  static const names = {
    'Gestational_Age',
    'Birth_Weight',
    'Sex',
    'Postnatal_Age',
    'Delivery_Mode',
    'Apgar',
    'HR',
    'Resp',
    'Temp',
    'SpO2',
    'BP',
    'Oxygen',
    'WBC',
    'CRP',
    'PCT',
    'Platelets',
    'Lactate',
    'Hemoglobin',
  };
  static const categories = {
    'Sex': ['Female', 'Male'],
    'Delivery_Mode': ['Cesarean', 'Vaginal'],
  };

  static Map<String, dynamic> prefill(PatientParameters patient, double age) {
    final result = <String, dynamic>{for (final name in names) name: null};
    // Raw dataset measurements are reused only as visible, editable research
    // inputs. Clinical laboratory fields have no verified dataset-unit mapping.
    for (final entry in patient.researchModelInputs.entries) {
      if (names.contains(entry.key)) result[entry.key] = entry.value;
    }
    result.addAll({
      'Gestational_Age': patient.gestationalAgeWeeks,
      'Birth_Weight': patient.birthWeightGrams == null
          ? null
          : patient.birthWeightGrams! / 1000,
      'Postnatal_Age': (age / 24).floor(),
      'Delivery_Mode': patient.deliveryMode == 'Caesarean'
          ? 'Cesarean'
          : patient.deliveryMode,
      'Apgar': patient.apgar5Min,
      'Temp':
          patient.hasCurrentResearchMeasurements &&
              patient.researchModelInputs.containsKey('Temp')
          ? patient.researchModelInputs['Temp']
          : patient.neonatalTemperature,
    });
    return result;
  }

  static Map<String, dynamic> payload(
    Map<String, dynamic> reviewed,
    double age,
  ) {
    if (!age.isFinite || age < 0 || age >= 72) {
      throw ArgumentError(
        'The installed research model supports ages below 72 hours.',
      );
    }
    if (reviewed.keys.toSet().difference(names).isNotEmpty ||
        names.difference(reviewed.keys.toSet()).isNotEmpty) {
      throw ArgumentError(
        'Research input fields do not match the installed model.',
      );
    }
    for (final entry in reviewed.entries) {
      final value = entry.value;
      if (value == null) continue;
      if (categories.containsKey(entry.key)) {
        if (!categories[entry.key]!.contains(value)) {
          throw ArgumentError('Unsupported category for ${entry.key}.');
        }
      } else if (value is! num || !value.isFinite) {
        throw ArgumentError('Only finite numeric measurements are accepted.');
      }
    }
    return {
      'input_contract_version': version,
      'purpose': 'research',
      'reviewed_inputs': true,
      'age_hours': age,
      'values': {...reviewed, 'Postnatal_Age': (age / 24).floor()},
    };
  }
}
