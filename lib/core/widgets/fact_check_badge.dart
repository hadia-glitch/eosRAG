import 'package:flutter/material.dart';
import '../../data/gemini_service.dart';
import '../../data/models/rag_chunk.dart';
import '../theme.dart';
import 'evidence_citation.dart';

/// Shows the result of the backend's Phase-3 fact-checking judge pass.
///
/// Renders nothing when the judge didn't run (`performed == false`) — that
/// happens for LOW/INTERMEDIATE risk (checked only for HIGH/CRITICAL, see
/// backend config.fact_check_categories) or when no LLM provider was
/// available. Absence of the badge should read as "not applicable", not as
/// a silent failure — the surrounding source banner already communicates
/// AI vs rule-based vs cached.
///
/// Stateful so flagged claims beyond the first are actually reachable: this
/// used to show "Unsupported claim: X (+4 more)" with no way to see the
/// other 4 — tapping the banner now expands the full list in place. The
/// backend also now caps flagged_claims at 4 total server-side (see
/// rag/fact_check.py's _MAX_FLAGGED_CLAIMS), so "more" is always a short,
/// genuinely readable list, not an unbounded pile-up.
///
/// Any `[E#]` token inside a flagged claim or note — the judge's own
/// prompt asks it to cite this way (see fact_check.py's
/// _build_judge_prompt) — renders as a hoverable/tappable citation chip
/// via [EvidenceCitationText] rather than plain text, using
/// [evidenceLabels] to resolve each label to its source.
///
/// The backend's step-by-step auto-resolution trail (what it tried to fix
/// and how) is intentionally NOT surfaced here — it's an internal
/// diagnostic (see ClinicalCarePlan.resolutionLog / gemini_service.py's
/// _resolve_flagged_claims), not something a clinician reading this plan
/// needs to see; what matters to them is only the end state this badge
/// already shows: verified, or here's what's still unverified.
class FactCheckBadge extends StatefulWidget {
  final FactCheckInfo factCheck;
  final Map<String, EvidenceLabelRef> evidenceLabels;

  const FactCheckBadge({
    super.key,
    required this.factCheck,
    this.evidenceLabels = const {},
  });

  @override
  State<FactCheckBadge> createState() => _FactCheckBadgeState();
}

class _FactCheckBadgeState extends State<FactCheckBadge> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final factCheck = widget.factCheck;
    if (!factCheck.performed) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Text(
          'Evidence verification not completed. Clinician review required.',
        ),
      );
    }

    if (factCheck.hasSeriousFlag) {
      return _buildBanner(
        icon: Icons.warning_amber_rounded,
        iconColor: WhoTheme.riskCritical,
        bgColor: WhoTheme.riskCritical.withValues(alpha: 0.1),
        borderColor: WhoTheme.riskCritical.withValues(alpha: 0.4),
        title: 'Fact-check flagged this output',
        titleColor: WhoTheme.riskCritical,
        claims: factCheck.flaggedClaims,
        fallbackSubtitle:
            'One or more claims could not be verified against the retrieved '
            'guideline evidence. Review before acting.',
      );
    }

    final hasMinorFlags = factCheck.flaggedClaims.isNotEmpty;
    return _buildBanner(
      icon: hasMinorFlags ? Icons.fact_check_outlined : Icons.verified_outlined,
      iconColor: hasMinorFlags
          ? WhoTheme.riskIntermediate
          : const Color(0xFF1A8A5F),
      bgColor: hasMinorFlags
          ? WhoTheme.riskIntermediate.withValues(alpha: 0.1)
          : const Color(0xFFE7F7EF),
      borderColor: hasMinorFlags
          ? WhoTheme.riskIntermediate.withValues(alpha: 0.4)
          : const Color(0xFFB7E4CC),
      title: hasMinorFlags
          ? 'Fact-checked · minor notes'
          : 'Source and safety checks passed; clinician review required',
      titleColor: hasMinorFlags
          ? WhoTheme.riskIntermediate
          : const Color(0xFF1A8A5F),
      claims: hasMinorFlags ? factCheck.flaggedClaims : const [],
      fallbackSubtitle: factCheck.notes,
      claimsLabel: hasMinorFlags
          ? '${factCheck.flaggedClaims.length} minor unsupported phrase'
                '${factCheck.flaggedClaims.length == 1 ? '' : 's'} noted — clinical '
                'recommendation unaffected.'
          : null,
    );
  }

  Widget _buildBanner({
    required IconData icon,
    required Color iconColor,
    required Color bgColor,
    required Color borderColor,
    required String title,
    required Color titleColor,
    required List<String> claims,
    required String fallbackSubtitle,
    String? claimsLabel,
  }) {
    final expandable = claims.isNotEmpty;

    return Container(
      margin: const EdgeInsets.only(top: 8),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: borderColor),
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: expandable
              ? () => setState(() => _expanded = !_expanded)
              : null,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(icon, size: 18, color: iconColor),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: TextStyle(
                                fontWeight: FontWeight.bold,
                                fontSize: 13,
                                color: titleColor,
                              ),
                            ),
                          ),
                          if (expandable)
                            Icon(
                              _expanded
                                  ? Icons.keyboard_arrow_up
                                  : Icons.keyboard_arrow_down,
                              size: 18,
                              color: titleColor,
                            ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      if (!expandable)
                        EvidenceCitationText(
                          text: fallbackSubtitle,
                          labels: widget.evidenceLabels,
                          style: TextStyle(
                            fontSize: 12,
                            color: titleColor.withValues(alpha: 0.85),
                          ),
                        )
                      else if (!_expanded)
                        Text(
                          claimsLabel ??
                              'Unsupported claim: ${claims.first}'
                                  '${claims.length > 1 ? ' — tap to view ${claims.length - 1} more' : ''}',
                          style: TextStyle(
                            fontSize: 12,
                            color: titleColor.withValues(alpha: 0.85),
                          ),
                        )
                      else
                        Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            if (claimsLabel != null) ...[
                              Text(
                                claimsLabel,
                                style: TextStyle(
                                  fontSize: 12,
                                  color: titleColor.withValues(alpha: 0.85),
                                ),
                              ),
                              const SizedBox(height: 6),
                            ],
                            ...claims.map(
                              (claim) => Padding(
                                padding: const EdgeInsets.only(bottom: 6),
                                child: Row(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      '•  ',
                                      style: TextStyle(
                                        fontSize: 12,
                                        color: titleColor.withValues(
                                          alpha: 0.85,
                                        ),
                                      ),
                                    ),
                                    Expanded(
                                      child: EvidenceCitationText(
                                        text: claim,
                                        labels: widget.evidenceLabels,
                                        style: TextStyle(
                                          fontSize: 12,
                                          color: titleColor.withValues(
                                            alpha: 0.85,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                            Text(
                              'Tap to collapse',
                              style: TextStyle(
                                fontSize: 11,
                                fontStyle: FontStyle.italic,
                                color: titleColor.withValues(alpha: 0.6),
                              ),
                            ),
                          ],
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
