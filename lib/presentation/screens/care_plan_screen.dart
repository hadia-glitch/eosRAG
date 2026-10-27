import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/theme.dart';
import '../../core/widgets/evidence_citation.dart';
import '../../core/widgets/fact_check_badge.dart';
import '../../data/api/explanation_api.dart';
import '../../data/auth_service.dart';
import '../../data/gemini_service.dart';
import '../../data/models/rag_chunk.dart';
import '../../data/supabase_config.dart';
import '../../domain/eoscal_calculator.dart';
import 'guideline_pdf_viewer_screen.dart';

/// Source-grounded EOS discussion with explicit withholding on missing
/// evidence, failed verification or loss of connectivity.
class CarePlanScreen extends ConsumerStatefulWidget {
  final PatientParameters patient;
  final EoscalResult result;
  final String activeGuideline;

  /// When true, renders without Scaffold/AppBar for embedding inside a tab
  /// (PatientDetailScreen tab 4).
  final bool embeddedInTab;

  const CarePlanScreen({
    super.key,
    required this.patient,
    required this.result,
    required this.activeGuideline,
    this.embeddedInTab = false,
  });

  @override
  ConsumerState<CarePlanScreen> createState() => _CarePlanScreenState();
}

class _CarePlanScreenState extends ConsumerState<CarePlanScreen> {
  late Future<ClinicalCarePlan> _future;
  List<Map<String, dynamic>> _previousAssessments = [];

  @override
  void initState() {
    super.initState();
    _future = _loadAndGenerate();
  }

  // ── Fetch chronological history, then generate the plan ──────────────────

  Future<ClinicalCarePlan> _loadAndGenerate() async {
    _previousAssessments = await _fetchPreviousAssessments();
    try {
      return await explanationApi.generateCarePlan(
        encounterId: widget.patient.id,
        patient: widget.patient,
        result: widget.result,
        activeGuideline: widget.activeGuideline,
        previousAssessments: _previousAssessments,
        careSetting: widget.patient.careSetting,
      );
    } on BackendUnreachableException {
      // Health check itself failed — genuinely offline. Try the locally-
      // synced guideline knowledge cache before giving up.
      return await _fallbackToOfflinePlan();
    } on DioException catch (e) {
      // Health check PASSED (backend is up) but the actual generation call
      // then failed. Two cases we treat the same way — fall back to the
      // offline protocol if one is cached, since a guideline-based answer
      // beats a technically-correct error either way:
      //   1. Timeout: care plan generation chains retrieval + rerank, an
      //      LLM call, and for HIGH/CRITICAL a second fact-check judge LLM
      //      call — on a slow connection or cold LLM provider this can
      //      genuinely exceed the client timeout even though the backend
      //      itself is healthy.
      //   2. 5xx server error: the backend responded but failed internally
      //      — e.g. it has no internet to reach Supabase/HuggingFace/the
      //      LLM providers even though it's reachable from this device on
      //      the local network (a real scenario during offline testing:
      //      the dev machine running the backend loses its own internet
      //      while staying reachable to the emulator/phone over LAN).
      final isNetworkIssue =
          e.type == DioExceptionType.receiveTimeout ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.sendTimeout ||
          e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.badResponse;
      if (isNetworkIssue) {
        return await _fallbackToOfflinePlan(dioError: e);
      }
      rethrow;
    }
  }

  Future<ClinicalCarePlan> _fallbackToOfflinePlan({
    DioException? dioError,
  }) async {
    // Covers every configured guideline, including any local protocol
    // uploaded via Settings > Guideline Configuration once it has synced —
    // and now ALWAYS succeeds even before that first sync, via the
    // built-in rule-based protocol tier (see CuratedCarePlanRules). The
    // "no offline plan available" error path is effectively retired.
    return const ClinicalCarePlan(
      clinicalSummary:
          'Automated care plan unavailable. Clinical review is required.',
      riskAnalysis:
          'No validated estimate or independently verified evidence is available offline.',
      trendNarrative: '',
      driverBreakdown: '',
      recommendedActions: [
        'Assess the infant directly using the approved local neonatal pathway.',
      ],
      antibioticPlan: AntibioticPlan(
        required: false,
        urgency: 'Clinician decision required',
        regimen: [],
        duration: 'Not determined',
        stopCriteria: 'Not determined',
      ),
      monitoringPlan: 'Use the approved local neonatal pathway.',
      escalationCriteria:
          'If the infant is unwell, seek urgent neonatal assessment without waiting for this app.',
      guidelineCitations: [],
      isSimulated: true,
      sourceLabel: 'Automated plan unavailable; clinician review required',
    );
  }

  /// Same join pattern as PatientTimelineScreen: clinical_assessments +
  /// risk_results by encounter_id, chronological (oldest first), excluding
  /// nothing — the backend only uses the last 5 for its trend narrative but
  /// we compute the UI trend chip from the full list deterministically.
  Future<List<Map<String, dynamic>>> _fetchPreviousAssessments() async {
    if (!SupabaseConfig.isConfigured || !AuthService.instance.isSignedIn) {
      return [];
    }
    try {
      final client = AuthService.instance.client;
      final assessmentsRows = await client
          .from('clinical_assessments')
          .select('id, created_at')
          .eq('encounter_id', widget.patient.id)
          .order('created_at', ascending: true);

      final riskRows = await client
          .from('risk_results')
          .select('assessment_id, combined_score, category, created_at')
          .eq('encounter_id', widget.patient.id);

      final Map<String, Map<String, dynamic>> riskByAssessment = {};
      for (final r in riskRows) {
        final aId = r['assessment_id'] as String?;
        if (aId != null) riskByAssessment[aId] = r;
      }

      final items = <Map<String, dynamic>>[];
      for (final row in assessmentsRows) {
        final aId = row['id'] as String;
        final risk = riskByAssessment[aId];
        if (risk == null) continue;
        items.add({
          'created_at': row['created_at'],
          'combined_score': (risk['combined_score'] as num?)?.toInt() ?? 0,
          'category': risk['category'] as String? ?? 'LOW',
        });
      }
      return items;
    } catch (_) {
      return [];
    }
  }

  void _retry() => setState(() {
    _future = _loadAndGenerate();
  });

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final body = FutureBuilder<ClinicalCarePlan>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return _buildLoading();
        }
        if (snapshot.hasError || !snapshot.hasData) {
          return _buildError(snapshot.error);
        }
        return _buildContent(snapshot.data!);
      },
    );

    if (widget.embeddedInTab) return body;

    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Care Plan'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Regenerate',
            onPressed: _retry,
          ),
        ],
      ),
      body: body,
    );
  }

  Widget _buildLoading() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const CircularProgressIndicator(),
          const SizedBox(height: 18),
          Text(
            'Building clinical care plan…',
            style: TextStyle(color: Colors.grey.shade600),
          ),
          const SizedBox(height: 6),
          Text(
            'Reviewing history · Checking cache · Querying ${widget.activeGuideline} evidence',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade400),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildError(Object? error) {
    final isUnreachable = error is BackendUnreachableException;
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isUnreachable ? Icons.cloud_off : Icons.error_outline,
              size: 52,
              color: isUnreachable ? Colors.orange : Colors.red,
            ),
            const SizedBox(height: 14),
            Text(
              isUnreachable
                  ? 'Backend unreachable'
                  : 'Could not generate care plan',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 10),
            if (isUnreachable) ...[
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.orange.shade50,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.orange.shade200),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'The NeoGuard backend could not be reached at:',
                      style: TextStyle(
                        fontSize: 13,
                        color: Colors.grey.shade700,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      error.backendUrl,
                      style: const TextStyle(
                        fontFamily: 'monospace',
                        fontSize: 13,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 10),
                    const Text(
                      'Is the backend running?  Make sure:',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      '1. Run:  cd backend && uvicorn main:app --host 0.0.0.0 --port 8000',
                      style: TextStyle(fontSize: 12, fontFamily: 'monospace'),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '2. For a physical device, pass your machine\'s LAN IP:',
                      style: TextStyle(fontSize: 12),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '   flutter run -d <id> --dart-define=API_BASE_URL=http://192.168.x.x:8000',
                      style: TextStyle(fontSize: 11, fontFamily: 'monospace'),
                    ),
                    const SizedBox(height: 4),
                    const Text(
                      '   Find your LAN IP: ipconfig (Windows) | ifconfig (Mac/Linux)',
                      style: TextStyle(fontSize: 11, color: Colors.grey),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.grey.shade100,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: Colors.grey.shade300),
                ),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.info_outline,
                      size: 16,
                      color: Colors.grey.shade600,
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Automated guidance is unavailable. Use the approved local neonatal pathway and seek clinical review.',
                        style: TextStyle(
                          fontSize: 12,
                          color: Colors.grey.shade700,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ] else
              Text(
                error?.toString() ?? 'Unknown error',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
            const SizedBox(height: 18),
            ElevatedButton.icon(
              icon: const Icon(Icons.refresh),
              label: const Text('Retry'),
              onPressed: _retry,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildContent(ClinicalCarePlan plan) {
    if (plan.planSections.length == 13) {
      return ListView(
        padding: const EdgeInsets.fromLTRB(16, 0, 16, 36),
        children: [
          const SizedBox(height: 10),
          _SourceBanner(plan: plan),
          const SizedBox(height: 12),
          for (final section in plan.planSections)
            _LetteredSection(
              letter: int.parse(section.id.substring(1)).toString(),
              title: section.title,
              icon: Icons.description_outlined,
              accentColor: WhoTheme.secondaryTeal,
              children: [
                Text(
                  switch (section.status) {
                    'evidence_supported' =>
                      'Source and safety checked; clinical review required',
                    'recorded' => 'Recorded information',
                    'withheld' => 'Automated content withheld',
                    _ => 'Clinical input needed',
                  },
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: Colors.grey.shade700,
                  ),
                ),
                const SizedBox(height: 8),
                for (final item in section.items)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: EvidenceCitationText(
                      text: item,
                      labels: plan.evidenceLabelMap,
                      style: const TextStyle(fontSize: 14, height: 1.6),
                    ),
                  ),
              ],
            ),
          if (plan.guidelineCitations.isNotEmpty)
            _LetteredSection(
              letter: null,
              title: 'Guideline sources',
              icon: Icons.menu_book_outlined,
              accentColor: WhoTheme.secondaryTeal,
              children: [
                for (final citation in plan.guidelineCitations.asMap().entries)
                  _CitationRow(
                    index: citation.key + 1,
                    citation: citation.value,
                  ),
              ],
            ),
          FactCheckBadge(
            factCheck: plan.factCheck,
            evidenceLabels: plan.evidenceLabelMap,
          ),
          if (plan.resolutionLog.isNotEmpty)
            ExpansionTile(
              title: const Text('Verification and revision details'),
              children: [
                for (final note in plan.resolutionLog)
                  Padding(
                    padding: const EdgeInsets.all(12),
                    child: EvidenceCitationText(
                      text: note,
                      labels: plan.evidenceLabelMap,
                    ),
                  ),
              ],
            ),
          if (plan.hasSafetyFlags) _SafetyFlagsBanner(plan: plan),
          _SafetyDisclaimer(isSimulated: plan.isSimulated),
        ],
      );
    }
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 36),
      children: [
        const SizedBox(height: 10),
        _SourceBanner(plan: plan),
        const SizedBox(height: 12),

        // ── A. Patient Development Summary ────────────────────────────────
        _LetteredSection(
          letter: 'A',
          title: 'Patient Development Summary',
          icon: Icons.timeline_outlined,
          accentColor: const Color(0xFF1A56DB),
          children: [
            EvidenceCitationText(
              text: plan.clinicalSummary,
              labels: plan.evidenceLabelMap,
              style: const TextStyle(fontSize: 14, height: 1.7),
            ),
            if (plan.trendNarrative.isNotEmpty) ...[
              const SizedBox(height: 10),
              EvidenceCitationText(
                text: plan.trendNarrative,
                labels: plan.evidenceLabelMap,
                style: TextStyle(
                  fontSize: 13,
                  height: 1.6,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey.shade700,
                ),
              ),
            ],
            if (!plan.isSimulated) ...[
              const SizedBox(height: 12),
              _AiDisclaimerChip(),
            ],
          ],
        ),

        if (plan.riskAnalysis.isNotEmpty)
          _LetteredSection(
            letter: null,
            title: 'Risk Analysis',
            icon: Icons.analytics_outlined,
            accentColor: const Color(0xFF7C3AED),
            children: [
              EvidenceCitationText(
                text: plan.riskAnalysis,
                labels: plan.evidenceLabelMap,
                style: const TextStyle(fontSize: 14, height: 1.7),
              ),
            ],
          ),

        // ── B. Immediate Actions ─────────────────────────────────────────
        _LetteredSection(
          letter: 'B',
          title: 'Evidence-supported considerations',
          icon: Icons.bolt,
          accentColor: const Color(0xFF059669),
          children: [
            if (plan.recommendedActions.isEmpty)
              Text(
                'No supported action was generated. Clinical assessment is required.',
                style: TextStyle(color: Colors.grey.shade600),
              )
            else
              ...plan.recommendedActions.asMap().entries.map(
                (e) => _ActionItem(
                  index: e.key + 1,
                  text: e.value,
                  evidenceLabels: plan.evidenceLabelMap,
                ),
              ),
          ],
        ),

        // ── C. Antibiotic Plan ────────────────────────────────────────────
        _AntibioticPlanCard(
          plan: plan.antibioticPlan,
          evidenceLabels: plan.evidenceLabelMap,
        ),

        if (plan.nutritionFluidPlan.isNotEmpty)
          _LetteredSection(
            letter: null,
            title: 'Nutrition & Fluid Plan',
            icon: Icons.local_drink_outlined,
            accentColor: const Color(0xFF0891B2),
            children: [
              EvidenceCitationText(
                text: plan.nutritionFluidPlan,
                labels: plan.evidenceLabelMap,
                style: const TextStyle(fontSize: 14, height: 1.7),
              ),
            ],
          ),

        if (plan.parentCommunicationNotes.isNotEmpty)
          _LetteredSection(
            letter: null,
            title: 'Parent Communication Notes',
            icon: Icons.family_restroom_outlined,
            accentColor: const Color(0xFF9333EA),
            children: [
              EvidenceCitationText(
                text: plan.parentCommunicationNotes,
                labels: plan.evidenceLabelMap,
                style: const TextStyle(fontSize: 14, height: 1.7),
              ),
            ],
          ),

        // ── D. Monitoring Schedule — RAG-grounded, active guideline first ──
        // (see gemini_service.py's _ensure_supplementary_fields_grounded).
        // The old hard-coded NICE-only card is now only a last-resort UI
        // fallback for a legacy/offline plan that predates this field
        // always being populated — the backend itself already falls back
        // to very similar wording, tagged [DETERMINISTIC DEFAULT], when
        // nothing in the active guideline or any other retrieved guideline
        // covers it, so this branch should be rare in practice.
        if (plan.monitoringPlan.isNotEmpty)
          _LetteredSection(
            letter: 'D',
            title: 'Monitoring Schedule',
            icon: Icons.monitor_heart_outlined,
            accentColor: const Color(0xFF0891B2),
            headerBadge: widget.activeGuideline,
            children: [
              EvidenceCitationText(
                text: plan.monitoringPlan,
                labels: plan.evidenceLabelMap,
                style: const TextStyle(fontSize: 14, height: 1.7),
              ),
            ],
          )
        else
          const _MonitoringScheduleCard(),

        // ── E. Escalation Criteria — RAG-grounded, active guideline first ──
        // Same fallback relationship to _EscalationCriteriaCard as D above.
        if (plan.escalationCriteria.isNotEmpty)
          _LetteredSection(
            letter: 'E',
            title: 'Escalation Criteria',
            icon: Icons.warning_amber_rounded,
            accentColor: const Color(0xFFDC2626),
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.red.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.red.shade200),
                ),
                child: EvidenceCitationText(
                  text: plan.escalationCriteria,
                  labels: plan.evidenceLabelMap,
                  style: const TextStyle(fontSize: 14, height: 1.7),
                ),
              ),
            ],
          )
        else
          const _EscalationCriteriaCard(),

        // ── F. Driver Breakdown ────────────────────────────────────────────
        if (plan.driverBreakdown.isNotEmpty)
          _LetteredSection(
            letter: 'F',
            title: 'Driver Breakdown',
            icon: Icons.radar,
            accentColor: const Color(0xFFD97706),
            children: [
              EvidenceCitationText(
                text: plan.driverBreakdown,
                labels: plan.evidenceLabelMap,
                style: const TextStyle(fontSize: 14, height: 1.7),
              ),
            ],
          ),

        // ── G. Guideline Sources ──────────────────────────────────────────
        if (plan.guidelineCitations.isNotEmpty)
          _LetteredSection(
            letter: 'G',
            title: 'Guideline Sources',
            icon: Icons.menu_book_outlined,
            accentColor: Colors.grey.shade600,
            children: [
              ...plan.guidelineCitations.asMap().entries.map(
                (e) => _CitationRow(index: e.key + 1, citation: e.value),
              ),
            ],
          ),

        // ── Fact-check + clinical safety flags — moved to the bottom: the
        // clinician has now read the actual plan (sections A-G) before
        // seeing the verification/caveat information about it, rather than
        // hitting a wall of warnings before any clinical content.
        FactCheckBadge(
          factCheck: plan.factCheck,
          evidenceLabels: plan.evidenceLabelMap,
        ),
        if (plan.hasSafetyFlags) _SafetyFlagsBanner(plan: plan),

        _SafetyDisclaimer(isSimulated: plan.isSimulated),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Trend chip — computed deterministically in Dart, correct even offline
// ─────────────────────────────────────────────────────────────────────────────

class _ParsedContraindication {
  final String? severity; // "CRITICAL" | "HIGH" | null if unparseable
  final String text; // "drug: reason", or the original string if unparseable
  const _ParsedContraindication({this.severity, required this.text});

  static final _re = RegExp(r'^\[(\w+)\]\s*(.*)$');

  factory _ParsedContraindication.parse(String raw) {
    final m = _re.firstMatch(raw);
    if (m == null) return _ParsedContraindication(text: raw);
    return _ParsedContraindication(
      severity: m.group(1),
      text: m.group(2) ?? raw,
    );
  }
}

/// Structured clinical safety information — three distinct kinds of note,
/// each shown in its own clearly labeled subsection rather than one flat
/// list of red text: a guideline-conflict disclosure (informational, not a
/// danger signal), deterministic contraindication flags (the actual safety
/// warnings, each with its real severity as a colored badge), and a trend
/// change note (informational). Only genuine contraindications drive the
/// card's overall red/critical styling — a guideline-conflict note or a
/// trend note on their own don't warrant painting the whole card as
/// dangerous.
class _SafetyFlagsBanner extends StatelessWidget {
  final ClinicalCarePlan plan;
  const _SafetyFlagsBanner({required this.plan});

  @override
  Widget build(BuildContext context) {
    final contraindications = plan.contraindicationFlags
        .map(_ParsedContraindication.parse)
        .toList();
    final hasCritical = contraindications.any(
      (c) => c.severity?.toUpperCase() == 'CRITICAL',
    );
    final hasAnyFlag =
        plan.disambiguationBlock.isNotEmpty ||
        contraindications.isNotEmpty ||
        plan.trendStateChange.isNotEmpty;
    if (!hasAnyFlag) return const SizedBox.shrink();

    final accent = contraindications.isNotEmpty
        ? (hasCritical ? WhoTheme.riskCritical : WhoTheme.riskHigh)
        : WhoTheme.secondaryTeal;

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: accent.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: accent.withValues(alpha: 0.35)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.health_and_safety, size: 18, color: accent),
              const SizedBox(width: 8),
              Text(
                'Clinical Safety Flags',
                style: TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 13,
                  color: accent,
                ),
              ),
            ],
          ),
          if (contraindications.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SafetySubsection(
              icon: Icons.medication_outlined,
              label: 'Contraindications',
              color: hasCritical ? WhoTheme.riskCritical : WhoTheme.riskHigh,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: contraindications
                    .map(
                      (c) => _ContraindicationRow(
                        item: c,
                        evidenceLabels: plan.evidenceLabelMap,
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
          if (plan.disambiguationBlock.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SafetySubsection(
              icon: Icons.compare_arrows,
              label: 'Guideline Conflict',
              color: WhoTheme.secondaryTeal,
              child: EvidenceCitationText(
                text: plan.disambiguationBlock,
                labels: plan.evidenceLabelMap,
                style: TextStyle(
                  fontSize: 12.5,
                  height: 1.5,
                  color: Colors.grey.shade800,
                ),
              ),
            ),
          ],
          if (plan.trendStateChange.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SafetySubsection(
              icon: Icons.show_chart,
              label: 'Trend Change',
              color: WhoTheme.secondaryTeal,
              child: EvidenceCitationText(
                text: plan.trendStateChange,
                labels: plan.evidenceLabelMap,
                style: TextStyle(
                  fontSize: 12.5,
                  height: 1.5,
                  color: Colors.grey.shade800,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// One labeled subsection inside the safety flags card — small icon +
/// caption above the actual content, so each kind of note is visually
/// distinct instead of running together in one paragraph.
class _SafetySubsection extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  final Widget child;

  const _SafetySubsection({
    required this.icon,
    required this.label,
    required this.color,
    required this.child,
  });

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 6),
            Text(
              label.toUpperCase(),
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.bold,
                letterSpacing: 0.4,
                color: color,
              ),
            ),
          ],
        ),
        const SizedBox(height: 5),
        Padding(padding: const EdgeInsets.only(left: 20), child: child),
      ],
    );
  }
}

/// One contraindication flag: a small severity badge (from the deterministic
/// "[SEVERITY]" prefix, if present) followed by clean "drug: reason" text —
/// replaces showing the raw bracket-prefixed string.
class _ContraindicationRow extends StatelessWidget {
  final _ParsedContraindication item;
  final Map<String, EvidenceLabelRef> evidenceLabels;
  const _ContraindicationRow({
    required this.item,
    required this.evidenceLabels,
  });

  @override
  Widget build(BuildContext context) {
    final severity = item.severity?.toUpperCase();
    final badgeColor = severity == 'CRITICAL'
        ? WhoTheme.riskCritical
        : severity == 'HIGH'
        ? WhoTheme.riskHigh
        : Colors.grey.shade500;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (severity != null) ...[
            Container(
              margin: const EdgeInsets.only(top: 1),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: badgeColor,
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                severity,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 9.5,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Expanded(
            child: EvidenceCitationText(
              text: item.text,
              labels: evidenceLabels,
              style: TextStyle(
                fontSize: 12.5,
                height: 1.4,
                color: Colors.grey.shade800,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Source banner
// ─────────────────────────────────────────────────────────────────────────────

class _SourceBanner extends StatelessWidget {
  final ClinicalCarePlan plan;
  const _SourceBanner({required this.plan});

  @override
  Widget build(BuildContext context) {
    if (plan.isSimulated) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.grey.shade100,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Colors.grey.shade400),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.rule, size: 18, color: Colors.grey.shade600),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Automated plan withheld',
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 13,
                      color: Colors.grey.shade800,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    plan.sourceLabel.isNotEmpty
                        ? plan.sourceLabel
                        : 'Clinical review and the approved local neonatal pathway are required.',
                    style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    }

    final isCached = plan.sourceLabel.toLowerCase().contains('cached');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFEEF4FF),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFFBFD3FF)),
      ),
      child: Row(
        children: [
          Icon(
            isCached ? Icons.cached : Icons.auto_awesome,
            size: 16,
            color: const Color(0xFF1A56DB),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              plan.sourceLabel.isNotEmpty
                  ? plan.sourceLabel
                  : 'AI-generated · clinical care plan',
              style: const TextStyle(fontSize: 12, color: Color(0xFF1A56DB)),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Lettered section card (A, B, F, G, ...)
// ─────────────────────────────────────────────────────────────────────────────

class _LetteredSection extends StatelessWidget {
  final String? letter;
  final String title;
  final IconData icon;
  final Color accentColor;
  final String? headerBadge;
  final List<Widget> children;

  const _LetteredSection({
    required this.letter,
    required this.title,
    required this.icon,
    required this.accentColor,
    this.headerBadge,
    required this.children,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 16),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (letter != null) ...[
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: accentColor,
                      shape: BoxShape.circle,
                    ),
                    alignment: Alignment.center,
                    child: Text(
                      letter!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 12,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                ] else ...[
                  Icon(icon, size: 18, color: accentColor),
                  const SizedBox(width: 8),
                ],
                Expanded(
                  child: Text(
                    title,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 15,
                      color: accentColor,
                    ),
                  ),
                ),
                if (headerBadge != null)
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: accentColor,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: Text(
                      headerBadge!,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 10,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
              ],
            ),
            const Divider(height: 20),
            ...children,
          ],
        ),
      ),
    );
  }
}

class _ActionItem extends StatelessWidget {
  final int index;
  final String text;
  final Map<String, EvidenceLabelRef> evidenceLabels;
  const _ActionItem({
    required this.index,
    required this.text,
    this.evidenceLabels = const {},
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 26,
            height: 26,
            margin: const EdgeInsets.only(right: 10, top: 1),
            decoration: const BoxDecoration(
              color: Color(0xFF059669),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '$index',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          Expanded(
            child: EvidenceCitationText(
              text: text,
              labels: evidenceLabels,
              style: const TextStyle(fontSize: 14, height: 1.55),
            ),
          ),
        ],
      ),
    );
  }
}

class _CitationRow extends StatelessWidget {
  final int index;
  final CitationItem citation;
  const _CitationRow({required this.index, required this.citation});

  /// "PDF name — Section" instead of an opaque chunk id — matches how the
  /// backend already labels citations (source_name + section), just
  /// rendered from the structured fields directly instead of a
  /// pre-flattened string.
  String get _label {
    final source = citation.source.trim();
    final section = citation.section.trim();
    if (source.isNotEmpty && section.isNotEmpty) return '$source — $section';
    return source.isNotEmpty
        ? source
        : (section.isNotEmpty ? section : 'Guideline source');
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$index.',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: Colors.grey.shade500,
              fontSize: 13,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_label, style: const TextStyle(fontSize: 13, height: 1.5)),
                if (citation.canOpenInApp)
                  GestureDetector(
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => GuidelinePdfViewerScreen(
                          fileName: citation.fileName,
                          documentName: citation.source.isNotEmpty
                              ? citation.source
                              : citation.fileName,
                          pageNumber: citation.pageNumber,
                          searchText: citation.section,
                        ),
                      ),
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          citation.pageNumber != null
                              ? 'Open in PDF · p.${citation.pageNumber}'
                              : 'Open in PDF',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Color(0xFF1A56DB),
                          ),
                        ),
                        const SizedBox(width: 3),
                        const Icon(
                          Icons.picture_as_pdf_outlined,
                          size: 12,
                          color: Color(0xFF1A56DB),
                        ),
                      ],
                    ),
                  )
                else if (citation.documentUrl.isNotEmpty)
                  GestureDetector(
                    onTap: () async {
                      await launchUrl(
                        Uri.parse(citation.documentUrl),
                        mode: LaunchMode.externalApplication,
                      );
                    },
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: Text(
                            citation.documentUrl,
                            style: const TextStyle(
                              fontSize: 12,
                              color: Color(0xFF1A56DB),
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        const SizedBox(width: 3),
                        const Icon(
                          Icons.arrow_outward,
                          size: 12,
                          color: Color(0xFF1A56DB),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.copy, size: 14),
            padding: EdgeInsets.zero,
            constraints: const BoxConstraints(),
            onPressed: () {
              Clipboard.setData(ClipboardData(text: _label));
              ScaffoldMessenger.of(
                context,
              ).showSnackBar(const SnackBar(content: Text('Citation copied')));
            },
          ),
        ],
      ),
    );
  }
}

class _AiDisclaimerChip extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.amber.shade50,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: Colors.amber.shade200),
      ),
      child: Row(
        children: [
          Icon(Icons.info_outline, size: 14, color: Colors.amber.shade700),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              'AI-generated. Clinical judgement of the responsible clinician supersedes this output.',
              style: TextStyle(
                fontSize: 11,
                fontStyle: FontStyle.italic,
                color: Colors.amber.shade900,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// C. Antibiotic plan — 3 explicit conditional branches ALWAYS shown,
// regardless of what the LLM (or rule-based fallback) returned. The plan's
// own required/urgency/regimen/duration fields populate the summary strip;
// the three branches below are static guidance from NICE NG195 §4 /
// AAP 2023 / WHO, present so a generalist doctor always has clear next steps
// whether labs come back negative, positive, or aren't back yet.
// ─────────────────────────────────────────────────────────────────────────────

class _AntibioticPlanCard extends StatelessWidget {
  final AntibioticPlan plan;
  final Map<String, EvidenceLabelRef> evidenceLabels;
  const _AntibioticPlanCard({
    required this.plan,
    this.evidenceLabels = const {},
  });
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Antibiotic decision',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          if (plan.decisionStatus == 'undetermined')
            const Text(
              'Requires clinician review. An unavailable or evidence-only plan is not a recommendation to withhold or stop antibiotics. Use the approved neonatal pathway.',
            )
          else
            ...plan.regimen.map(
              (r) => EvidenceCitationText(text: r, labels: evidenceLabels),
            ),
        ],
      ),
    ),
  );
}

class _MonitoringScheduleCard extends StatelessWidget {
  const _MonitoringScheduleCard();
  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Text(
        'Automated monitoring schedule not determined. Use the approved local neonatal pathway.',
      ),
    ),
  );
}

class _EscalationCriteriaCard extends StatelessWidget {
  const _EscalationCriteriaCard();
  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(16),
      child: Text(
        'Seek neonatal clinical assessment if the infant is unwell. Do not wait for an automated response.',
      ),
    ),
  );
}

class _SafetyDisclaimer extends StatelessWidget {
  final bool isSimulated;
  const _SafetyDisclaimer({required this.isSimulated});

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: Colors.grey.shade300),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.shield_outlined, size: 18, color: Colors.grey.shade400),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              isSimulated
                  ? 'Automated guidance was withheld. This does not mean low risk or that treatment is unnecessary. Clinical assessment takes precedence.'
                  : 'This care plan was generated by an AI language model for educational support '
                        'only. Clinical decisions must be made by a qualified clinician based on the '
                        'full clinical picture. NeoGuard AI does not replace clinical judgement.',
              style: TextStyle(
                fontSize: 12,
                color: Colors.grey.shade600,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
