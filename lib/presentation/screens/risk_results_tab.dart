import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../core/theme.dart';
import '../../core/widgets/ml_risk_card.dart';
import '../../domain/eoscal_calculator.dart';
import 'explanation_screen.dart';
import '../patient_state.dart';

/// Screen 14 content — Risk Assessment Results
class RiskResultsTab extends ConsumerStatefulWidget {
  final PatientParameters patient;
  final String activeGuideline;
  final bool compact;

  const RiskResultsTab({
    super.key,
    required this.patient,
    required this.activeGuideline,
    this.compact = false,
  });

  @override
  ConsumerState<RiskResultsTab> createState() => _RiskResultsTabState();
}

class _RiskResultsTabState extends ConsumerState<RiskResultsTab> {
  late String _guideline;

  @override
  void initState() {
    super.initState();
    _guideline = widget.activeGuideline;
  }

  @override
  Widget build(BuildContext context) {
    final patient = ref
        .watch(patientsProvider)
        .firstWhere(
          (p) => p.id == widget.patient.id,
          orElse: () => widget.patient,
        );
    final result = EoscalCalculator.calculate(patient);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          MlRiskCard(patient: patient),
          if (result.belowEoscalScope)
            Container(
              margin: const EdgeInsets.only(top: 8),
              padding: const EdgeInsets.all(12),
              color: WhoTheme.riskIntermediate.withValues(alpha: 0.2),
              child: const Text(
                'Preterm infant: model applicability must match the development cohort.',
              ),
            ),
          const SizedBox(height: 16),
          Wrap(
            spacing: 8,
            children: ['NICE', 'AAP', 'WHO'].map((g) {
              final active = _guideline == g;
              return ChoiceChip(
                label: Text(g),
                selected: active,
                onSelected: (_) => setState(() => _guideline = g),
              );
            }).toList(),
          ),
          const SizedBox(height: 12),

          if (!widget.compact) ...[
            const SizedBox(height: 16),
            SizedBox(
              width: double.infinity,
              child: OutlinedButton.icon(
                onPressed: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ExplanationScreen(
                      patient: patient,
                      result: result,
                      activeGuideline: _guideline,
                    ),
                  ),
                ),
                icon: const Icon(Icons.psychology),
                label: const Text('View Clinical Explanation →'),
                style: OutlinedButton.styleFrom(
                  foregroundColor: WhoTheme.secondaryTeal,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
