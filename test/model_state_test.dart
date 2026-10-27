import 'package:flutter_test/flutter_test.dart';
import 'package:eos/domain/eoscal_calculator.dart';
import 'package:eos/data/gemini_service.dart';

void main() {
  test('Live workflow cannot produce a legacy point-based assessment', () {
    final patient = PatientParameters(
      id: 'test',
      name: 'Synthetic fixture',
      mrn: 'TEST',
      gestationalAgeWeeks: 38,
      birthDateTime: DateTime(2026, 10, 24),
      maternalTemperature: 39.5,
      romHours: 30,
      gbsPositive: true,
      adequateIntrapartumAntibiotics: false,
      clinicalChorioamnionitis: true,
      deliveryMode: 'Vaginal',
      respiratoryDistress: 'Severe',
      oxygenNeed: 'CPAP/Ventilation',
      apgar5Min: 5,
      poorPerfusion: true,
      neonatalTemperature: 38.5,
      neurologicalStatus: 'Irritable/Lethargic',
    );
    final result = EoscalCalculator.calculate(patient);
    expect(result.hasValidatedRisk, isFalse);
    expect(result.riskLabel, 'Not assessed');
    expect(result.allDrivers, isEmpty);
    expect(result.warnings, isNotEmpty);
  });

  test('Missing verification and medication decisions remain undetermined', () {
    final verification = FactCheckInfo.fromJson(null);
    expect(verification.verified, isFalse);
    expect(verification.performed, isFalse);
    final plan = AntibioticPlan.fromJson({});
    expect(plan.decisionStatus, 'undetermined');
    expect(plan.urgency, 'Clinician decision required');
    expect(plan.stopCriteria, contains('Not determined'));
  });
}
