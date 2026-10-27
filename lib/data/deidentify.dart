import '../domain/eoscal_calculator.dart';

/// De-identified patient snapshot for backend API calls (Section 8.1).
///
/// Extended to full parity with what's actually captured per assessment
/// (see patient_state.dart's _upsertClinicalTables) -- previously only 10 of
/// ~20 fields reached the backend, so query construction and generation
/// prompts couldn't see delivery mode, chorioamnionitis, oxygen need, apgar,
/// perfusion, neuro status, or any lab value except CRP/blood culture.
class DeidentifiedPatient {
  final double? gestationalAgeWeeks;
  final double? maternalTemperature;
  final double? romHours;
  final bool? gbsPositive;
  final String? respiratoryDistress;
  final double? crpLevel;
  final bool? bloodCulturePositive;
  final double? urineOutputMlKgHr;
  final double? creatinineMgDl;
  final bool? penicillinAllergy;
  final bool? adequateIntrapartumAntibiotics;
  final bool? clinicalChorioamnionitis;
  final String? deliveryMode;
  final String? oxygenNeed;
  final int? apgar5Min;
  final bool? poorPerfusion;
  final double? neonatalTemperature;
  final String? neurologicalStatus;
  final double? wbcCount;
  final double? itRatio;
  final double? plateletCount;
  final double? pctLevel;
  // Not previously exposed to the backend at all -- see
  // patient_entry_flow.dart / new_patient_screen.dart for where this is
  // actually captured now. Feeds rag/query_builder.py's low-birth-weight
  // query terms and domain/contraindication_rules.check_who_outpatient_exclusions
  // on the backend (both via schemas.PatientSnapshot.birth_weight_g).
  final double? birthWeightGrams;
  final double? heartRate;
  final double? respiratoryRate;
  final double? spo2;

  const DeidentifiedPatient({
    this.gestationalAgeWeeks,
    this.maternalTemperature,
    this.romHours,
    this.gbsPositive,
    this.respiratoryDistress,
    this.crpLevel,
    this.bloodCulturePositive,
    this.urineOutputMlKgHr,
    this.creatinineMgDl,
    this.penicillinAllergy,
    this.adequateIntrapartumAntibiotics,
    this.clinicalChorioamnionitis,
    this.deliveryMode,
    this.oxygenNeed,
    this.apgar5Min,
    this.poorPerfusion,
    this.neonatalTemperature,
    this.neurologicalStatus,
    this.wbcCount,
    this.itRatio,
    this.plateletCount,
    this.pctLevel,
    this.birthWeightGrams,
    this.heartRate,
    this.respiratoryRate,
    this.spo2,
  });

  Map<String, dynamic> toJson() => {
    if (gestationalAgeWeeks != null)
      'gestational_age_weeks': gestationalAgeWeeks,
    if (maternalTemperature != null)
      'maternal_temperature': maternalTemperature,
    if (romHours != null) 'rom_hours': romHours,
    if (gbsPositive != null) 'gbs_positive': gbsPositive,
    if (respiratoryDistress != null)
      'respiratory_distress': respiratoryDistress,
    if (crpLevel != null) 'crp_level': crpLevel,
    if (bloodCulturePositive != null)
      'blood_culture_positive': bloodCulturePositive,
    if (urineOutputMlKgHr != null) 'urine_output_ml_kg_hr': urineOutputMlKgHr,
    if (creatinineMgDl != null) 'creatinine_mg_dl': creatinineMgDl,
    if (penicillinAllergy != null) 'penicillin_allergy': penicillinAllergy,
    if (adequateIntrapartumAntibiotics != null)
      'adequate_intrapartum_antibiotics': adequateIntrapartumAntibiotics,
    if (clinicalChorioamnionitis != null)
      'clinical_chorioamnionitis': clinicalChorioamnionitis,
    if (deliveryMode != null) 'delivery_mode': deliveryMode,
    if (oxygenNeed != null) 'oxygen_need': oxygenNeed,
    if (apgar5Min != null) 'apgar_5_min': apgar5Min,
    if (poorPerfusion != null) 'poor_perfusion': poorPerfusion,
    if (neonatalTemperature != null)
      'neonatal_temperature': neonatalTemperature,
    if (neurologicalStatus != null) 'neurological_status': neurologicalStatus,
    if (wbcCount != null) 'wbc_count': wbcCount,
    if (itRatio != null) 'it_ratio': itRatio,
    if (plateletCount != null) 'platelet_count': plateletCount,
    if (pctLevel != null) 'pct_level': pctLevel,
    if (birthWeightGrams != null) 'birth_weight_g': birthWeightGrams,
    if (heartRate != null) 'heart_rate': heartRate,
    if (respiratoryRate != null) 'respiratory_rate': respiratoryRate,
    if (spo2 != null) 'spo2': spo2,
  };

  static DeidentifiedPatient fromPatient(PatientParameters p) {
    return DeidentifiedPatient(
      gestationalAgeWeeks: p.gestationalAgeWeeks,
      maternalTemperature: p.maternalTemperature,
      romHours: p.romHours,
      gbsPositive: p.gbsPositive,
      respiratoryDistress: p.respiratoryDistress,
      crpLevel: p.crpLevel,
      bloodCulturePositive: p.bloodCulturePositive,
      urineOutputMlKgHr: p.urineOutputMlKgHr,
      creatinineMgDl: p.creatinineMgDl,
      penicillinAllergy: p.penicillinAllergy,
      adequateIntrapartumAntibiotics: p.adequateIntrapartumAntibiotics,
      clinicalChorioamnionitis: p.clinicalChorioamnionitis,
      deliveryMode: p.deliveryMode,
      oxygenNeed: p.oxygenNeed,
      apgar5Min: p.apgar5Min,
      poorPerfusion: p.poorPerfusion,
      neonatalTemperature:
          p.hasCurrentResearchMeasurements &&
              p.researchModelInputs.containsKey('Temp') &&
              p.researchModelInputs['Temp'] == null
          ? null
          : p.neonatalTemperature,
      neurologicalStatus: p.neurologicalStatus,
      wbcCount: p.wbcCount,
      itRatio: p.itRatio,
      plateletCount: p.plateletCount,
      pctLevel: p.pctLevel,
      birthWeightGrams: p.birthWeightGrams,
      heartRate: p.hasCurrentResearchMeasurements
          ? (p.researchModelInputs['HR'] as num?)?.toDouble()
          : null,
      respiratoryRate: p.hasCurrentResearchMeasurements
          ? (p.researchModelInputs['Resp'] as num?)?.toDouble()
          : null,
      spo2: p.hasCurrentResearchMeasurements
          ? (p.researchModelInputs['SpO2'] as num?)?.toDouble()
          : null,
    );
  }
}

/// De-identified risk payload for RAG + Gemini endpoints.
Map<String, dynamic> buildRiskPayload(
  PatientParameters patient,
  EoscalResult result,
) {
  return {
    'patient': {
      ...DeidentifiedPatient.fromPatient(patient).toJson(),
      'age_hours':
          DateTime.now()
              .toUtc()
              .difference(patient.birthDateTime.toUtc())
              .inSeconds /
          3600,
    },
    'warnings': result.warnings,
  };
}
