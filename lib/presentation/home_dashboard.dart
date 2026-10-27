import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/theme.dart';
import '../data/auth_service.dart';
import '../data/supabase_config.dart';
import '../domain/eoscal_calculator.dart';
import '../data/guidelines_data.dart';
import 'patient_state.dart';
import 'screens/evidence_search_screen.dart';
import 'screens/patient_detail_screen.dart';
import 'screens/care_plan_screen.dart';

class HomeDashboard extends ConsumerStatefulWidget {
  final int initialTab;
  const HomeDashboard({super.key, this.initialTab = 0});

  @override
  ConsumerState<HomeDashboard> createState() => _HomeDashboardState();
}

class _HomeDashboardState extends ConsumerState<HomeDashboard> {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    _currentIndex = widget.initialTab;
    // Refresh patients from Supabase every time the dashboard is entered so
    // a freshly-logged-in user sees their full patient list immediately.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(patientsProvider.notifier).refresh();
    });
  }

  @override
  Widget build(BuildContext context) {
    final List<Widget> tabs = [
      const DashboardTab(),
      const PatientsTab(),
      EvidenceSearchScreen(),
      const AlertsTab(),
      const SettingsTab(),
    ];

    return Scaffold(
      appBar: AppBar(
        title: FittedBox(
          fit: BoxFit.scaleDown,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.security, color: Colors.white, size: 24),
              const SizedBox(width: 8),
              Text(
                'NEOGUARD AI',
                style: Theme.of(context).appBarTheme.titleTextStyle,
              ),
            ],
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Sign out',
            onPressed: () async {
              await AuthService.instance.signOut();
              if (!mounted) return;
              this.context.go('/login');
            },
          ),
        ],
      ),
      body: SafeArea(
        child: IndexedStack(index: _currentIndex, children: tabs),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/new-patient'),
        icon: const Icon(Icons.add),
        label: const Text('New Assessment'),
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        type: BottomNavigationBarType.fixed,
        backgroundColor: WhoTheme.primaryNavy,
        selectedItemColor: Colors.white,
        unselectedItemColor: Colors.white60,
        selectedLabelStyle: const TextStyle(
          fontWeight: FontWeight.bold,
          fontSize: 12,
        ),
        unselectedLabelStyle: const TextStyle(fontSize: 11),
        items: const [
          BottomNavigationBarItem(
            icon: Icon(Icons.dashboard_outlined),
            activeIcon: Icon(Icons.dashboard),
            label: 'Home',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.people_alt_outlined),
            activeIcon: Icon(Icons.people_alt),
            label: 'Patients',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.menu_book_outlined),
            activeIcon: Icon(Icons.menu_book),
            label: 'Evidence',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.warning_amber_outlined),
            activeIcon: Icon(Icons.warning),
            label: 'Alerts',
          ),
          BottomNavigationBarItem(
            icon: Icon(Icons.settings_outlined),
            activeIcon: Icon(Icons.settings),
            label: 'Settings',
          ),
        ],
      ),
    );
  }
}

// ==========================================
// 1. DASHBOARD TAB
// ==========================================
class DashboardTab extends ConsumerWidget {
  const DashboardTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final patients = ref.watch(patientsProvider);
    final activeGuideline = ref.watch(activeGuidelineProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Ward Overview',
                style: Theme.of(context).textTheme.headlineMedium,
              ),
              const SizedBox(height: 2),
              Text(
                'Active Guidance: $activeGuideline Sepsis Engine',
                style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 20),

          // Risk Summary Grid
          GridView.count(
            crossAxisCount: 2,
            crossAxisSpacing: 12,
            mainAxisSpacing: 12,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            childAspectRatio: 1.6,
            children: [
              _buildStatCard('Patients', patients.length, WhoTheme.primaryNavy),
              _buildStatCard('Not assessed', patients.length, Colors.blueGrey),
            ],
          ),
          const SizedBox(height: 24),

          Text(
            'Recent Assessments',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 10),
          patients.isEmpty
              ? Container(
                  padding: const EdgeInsets.all(32),
                  alignment: Alignment.center,
                  child: Text(
                    'No patients registered. Tap "New Assessment" to start.',
                    style: TextStyle(color: Colors.grey.shade500),
                  ),
                )
              : ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: patients.length > 10 ? 10 : patients.length,
                  itemBuilder: (context, index) {
                    final patient = patients[index];
                    final result = EoscalCalculator.calculate(patient);
                    return PatientListTile(patient: patient, result: result);
                  },
                ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String label, int value, Color color) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border(left: BorderSide(color: color, width: 6)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 6,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Flexible(
            child: Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: WhoTheme.neutralDarkGrey,
              ),
            ),
          ),
          const SizedBox(height: 4),
          FittedBox(
            child: Text(
              '$value',
              style: TextStyle(
                fontSize: 32,
                fontWeight: FontWeight.bold,
                color: color,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ==========================================
// 2. PATIENTS TAB
// ==========================================
class PatientsTab extends ConsumerWidget {
  const PatientsTab({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final searchQuery = ref.watch(searchQueryProvider);
    final patients = ref.watch(patientsProvider);

    final filteredPatients = patients.where((p) {
      final query = searchQuery.toLowerCase();
      return p.name.toLowerCase().contains(query) ||
          p.mrn.toLowerCase().contains(query);
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Patient Registry',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          TextField(
            onChanged: (val) =>
                ref.read(searchQueryProvider.notifier).state = val,
            decoration: InputDecoration(
              hintText: 'Search patients by name or MRN...',
              prefixIcon: const Icon(Icons.search, color: WhoTheme.primaryNavy),
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: filteredPatients.isEmpty
                ? Center(
                    child: Text(
                      searchQuery.isEmpty
                          ? 'No patients enrolled in registry.'
                          : 'No matching patients found.',
                      style: TextStyle(color: Colors.grey.shade500),
                    ),
                  )
                : ListView.builder(
                    itemCount: filteredPatients.length,
                    itemBuilder: (context, index) {
                      final patient = filteredPatients[index];
                      final result = EoscalCalculator.calculate(patient);
                      return PatientListTile(patient: patient, result: result);
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ==========================================
// 3. EVIDENCE TAB
// ==========================================
class EvidenceTab extends StatefulWidget {
  const EvidenceTab({super.key});

  @override
  State<EvidenceTab> createState() => _EvidenceTabState();
}

class _EvidenceTabState extends State<EvidenceTab> {
  String _selectedSource = 'ALL';
  String _searchQuery = '';

  @override
  Widget build(BuildContext context) {
    final filteredChunks = GuidelinesData.chunks.where((chunk) {
      final matchesSource =
          _selectedSource == 'ALL' || chunk.source == _selectedSource;
      final matchesSearch =
          chunk.content.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          chunk.section.toLowerCase().contains(_searchQuery.toLowerCase()) ||
          chunk.keywords.any(
            (k) => k.toLowerCase().contains(_searchQuery.toLowerCase()),
          );
      return matchesSource && matchesSearch;
    }).toList();

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Guidelines & Evidence',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 12),
          // Search Guideline
          TextField(
            onChanged: (val) {
              setState(() {
                _searchQuery = val;
              });
            },
            decoration: InputDecoration(
              hintText: 'Search evidence keywords (e.g. antibiotic, CRP)...',
              prefixIcon: const Icon(Icons.search, color: WhoTheme.primaryNavy),
            ),
          ),
          const SizedBox(height: 12),
          // Filter Chips
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: ['ALL', 'NICE', 'AAP', 'WHO'].map((source) {
                final isSelected = _selectedSource == source;
                return Padding(
                  padding: const EdgeInsets.only(right: 8.0),
                  child: FilterChip(
                    label: Text(source),
                    selected: isSelected,
                    selectedColor: WhoTheme.primaryNavy.withValues(alpha: 0.15),
                    checkmarkColor: WhoTheme.primaryNavy,
                    labelStyle: TextStyle(
                      color: isSelected
                          ? WhoTheme.primaryNavy
                          : WhoTheme.neutralDarkGrey,
                      fontWeight: isSelected
                          ? FontWeight.bold
                          : FontWeight.normal,
                    ),
                    onSelected: (selected) {
                      setState(() {
                        _selectedSource = source;
                      });
                    },
                  ),
                );
              }).toList(),
            ),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: filteredChunks.isEmpty
                ? Center(
                    child: Text(
                      'No matching guideline guidelines found.',
                      style: TextStyle(color: Colors.grey.shade500),
                    ),
                  )
                : ListView.builder(
                    itemCount: filteredChunks.length,
                    itemBuilder: (context, index) {
                      final chunk = filteredChunks[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                mainAxisAlignment:
                                    MainAxisAlignment.spaceBetween,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 8,
                                      vertical: 4,
                                    ),
                                    decoration: BoxDecoration(
                                      color: WhoTheme.primaryNavy.withValues(
                                        alpha: 0.1,
                                      ),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      chunk.source,
                                      style: const TextStyle(
                                        color: WhoTheme.primaryNavy,
                                        fontWeight: FontWeight.bold,
                                        fontSize: 12,
                                      ),
                                    ),
                                  ),
                                  Text(
                                    chunk.section,
                                    style: TextStyle(
                                      color: Colors.grey.shade600,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w600,
                                    ),
                                  ),
                                ],
                              ),
                              const SizedBox(height: 10),
                              Text(
                                chunk.content,
                                style: const TextStyle(
                                  fontSize: 14,
                                  color: WhoTheme.neutralDarkGrey,
                                  height: 1.4,
                                ),
                              ),
                              const SizedBox(height: 8),
                              Wrap(
                                spacing: 6,
                                runSpacing: 4,
                                children: chunk.keywords.map((k) {
                                  return Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 6,
                                      vertical: 2,
                                    ),
                                    decoration: BoxDecoration(
                                      color: Colors.grey.shade100,
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Text(
                                      '#$k',
                                      style: TextStyle(
                                        color: Colors.grey.shade600,
                                        fontSize: 11,
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ),
                            ],
                          ),
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ==========================================
// 4. ALERTS TAB
// ==========================================
class AlertsTab extends ConsumerStatefulWidget {
  const AlertsTab({super.key});

  @override
  ConsumerState<AlertsTab> createState() => _AlertsTabState();
}

class _AlertsTabState extends ConsumerState<AlertsTab> {
  List<Map<String, dynamic>> _activeAlerts = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _loadAlertsFromDb();
  }

  Future<void> _loadAlertsFromDb() async {
    if (!SupabaseConfig.isConfigured || !AuthService.instance.isSignedIn) {
      if (mounted) {
        setState(() {
          _activeAlerts = [];
          _loading = false;
        });
      }
      return;
    }

    final patients = ref.read(patientsProvider);
    if (patients.isEmpty) {
      if (mounted) {
        setState(() {
          _activeAlerts = [];
          _loading = false;
        });
      }
      return;
    }

    final encounterIds = patients.map((p) => p.id).toList();
    final patientById = {for (final p in patients) p.id: p};

    try {
      final client = AuthService.instance.client;
      final rows = await client
          .from('alerts')
          .select(
            'encounter_id, alert_type, priority, action_taken, created_at',
          )
          .inFilter('encounter_id', encounterIds)
          .order('created_at', ascending: false);

      final alerts = <Map<String, dynamic>>[];
      for (final row in rows as List<dynamic>) {
        final m = row as Map<String, dynamic>;
        final encounterId = m['encounter_id'] as String?;
        if (encounterId == null) continue;
        final patient = patientById[encounterId];
        if (patient == null) continue;

        final res = EoscalCalculator.calculate(patient);
        final alertType = m['alert_type'] as String? ?? 'risk';
        final priority = m['priority'] as String? ?? 'MEDIUM';
        alerts.add({
          'patient': patient,
          'result': res,
          'type': alertType,
          'severity': _severityFromAlert(priority, alertType, res.riskCategory),
          'message': m['action_taken'] as String? ?? 'Clinical alert active.',
        });
      }

      if (mounted) {
        setState(() {
          _activeAlerts = alerts;
          _loading = false;
        });
      }
    } catch (e) {
      debugPrint('AlertsTab DB query failed: $e');
      if (mounted) {
        setState(() {
          _activeAlerts = [];
          _loading = false;
        });
      }
    }
  }

  RiskCategory _severityFromAlert(
    String priority,
    String alertType,
    RiskCategory defaultRisk,
  ) {
    switch (priority.toUpperCase()) {
      case 'CRITICAL':
        return RiskCategory.critical;
      case 'HIGH':
        return RiskCategory.high;
      case 'MEDIUM':
        return RiskCategory.intermediate;
      default:
        if (alertType == 'culture') return RiskCategory.critical;
        return defaultRisk;
    }
  }

  @override
  Widget build(BuildContext context) {
    ref.listen<List<PatientParameters>>(patientsProvider, (_, _) {
      _loadAlertsFromDb();
    });

    final activeAlerts = _activeAlerts;

    return Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Clinical Warnings & Audits',
            style: Theme.of(context).textTheme.headlineMedium,
          ),
          const SizedBox(height: 4),
          Text(
            'Real-time alerts active across current ward roster.',
            style: TextStyle(color: Colors.grey.shade600, fontSize: 13),
          ),
          const SizedBox(height: 16),
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : activeAlerts.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.check_circle_outline,
                          size: 64,
                          color: WhoTheme.riskLow,
                        ),
                        const SizedBox(height: 12),
                        const Text(
                          'No critical alerts active.',
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 16,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'No automated alert is not evidence of low EOS risk.',
                          style: TextStyle(color: Colors.grey.shade500),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    itemCount: activeAlerts.length,
                    itemBuilder: (context, index) {
                      final alert = activeAlerts[index];
                      final PatientParameters patient = alert['patient'];
                      final RiskCategory severity = alert['severity'];

                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(
                            color: severity.color.withValues(alpha: 0.4),
                            width: 1,
                          ),
                        ),
                        child: ListTile(
                          leading: CircleAvatar(
                            backgroundColor: severity.color.withValues(
                              alpha: 0.15,
                            ),
                            child: Icon(
                              Icons.warning,
                              color: severity.color,
                              size: 20,
                            ),
                          ),
                          title: Text(
                            patient.name,
                            style: const TextStyle(fontWeight: FontWeight.bold),
                          ),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: 2),
                              Text(alert['message']),
                              const SizedBox(height: 4),
                              Row(
                                children: [
                                  Text(
                                    'Risk not assessed | MRN: ${patient.mrn}',
                                    style: TextStyle(
                                      fontSize: 12,
                                      color: Colors.grey.shade600,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                          isThreeLine: true,
                          trailing: const Icon(
                            Icons.arrow_forward_ios,
                            size: 14,
                          ),
                          onTap: () {
                            final guideline = ref.read(activeGuidelineProvider);
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => PatientDetailScreen(
                                  patient: patient,
                                  activeGuideline: guideline,
                                ),
                              ),
                            );
                          },
                        ),
                      );
                    },
                  ),
          ),
        ],
      ),
    );
  }
}

// ==========================================
// 5. SETTINGS TAB
// ==========================================
class SettingsTab extends ConsumerStatefulWidget {
  const SettingsTab({super.key});

  @override
  ConsumerState<SettingsTab> createState() => _SettingsTabState();
}

class _SettingsTabState extends ConsumerState<SettingsTab> {
  @override
  Widget build(BuildContext context) {
    final guideline = ref.watch(activeGuidelineProvider);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          'Settings & Configuration',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 20),
        const Text(
          'Guideline for evidence retrieval',
          style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
        ),
        const Text(
          'Only reviewed, current passages applicable to the patient can support generated discussion points.',
        ),
        const SizedBox(height: 12),
        Wrap(
          spacing: 10,
          children: ['NICE', 'AAP', 'WHO']
              .map(
                (g) => ChoiceChip(
                  label: Text(g),
                  selected: guideline == g,
                  onSelected: (_) => ref
                      .read(activeGuidelineProvider.notifier)
                      .setGuideline(g),
                ),
              )
              .toList(),
        ),
        const SizedBox(height: 24),
        const Card(
          child: Padding(
            padding: EdgeInsets.all(16),
            child: Text(
              'AI generation and model releases are managed by the backend administrator. No provider key is stored in this app. Numerical estimates require an installed model; evidence checks require clinician review.',
            ),
          ),
        ),
        const SizedBox(height: 24),
        Text('Administration', style: Theme.of(context).textTheme.titleLarge),
        Card(
          child: Column(
            children: [
              ListTile(
                leading: const Icon(Icons.library_books_outlined),
                title: const Text('Guideline Configuration'),
                onTap: () => context.push('/admin/guidelines'),
              ),
              ListTile(
                leading: const Icon(Icons.history),
                title: const Text('Audit Log'),
                onTap: () => context.push('/admin/audit'),
              ),
            ],
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'NeoGuard EOS - research decision support. Clinical validation is required.',
        ),
      ],
    );
  }
}

// ==========================================
// SHARED REUSABLE COMPONENTS
// ==========================================
class PatientListTile extends ConsumerWidget {
  final PatientParameters patient;
  final EoscalResult result;

  const PatientListTile({
    super.key,
    required this.patient,
    required this.result,
  });

  void _openExplanation(BuildContext context, WidgetRef ref) {
    final guideline = ref.read(activeGuidelineProvider);
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => CarePlanScreen(
          patient: patient,
          result: result,
          activeGuideline: guideline,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ageHours = DateTime.now().difference(patient.birthDateTime).inHours;
    final riskColor = result.hasValidatedRisk
        ? result.riskCategory.color
        : Colors.blueGrey;

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () {
          final guideline = ref.read(activeGuidelineProvider);
          Navigator.push(
            context,
            MaterialPageRoute(
              builder: (context) => PatientDetailScreen(
                patient: patient,
                activeGuideline: guideline,
              ),
            ),
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              // Risk score badge
              Container(
                width: 48,
                height: 48,
                decoration: BoxDecoration(
                  color: riskColor.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                  border: Border.all(color: riskColor, width: 2),
                ),
                alignment: Alignment.center,
                child: Text(
                  '--',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.bold,
                    color: riskColor,
                  ),
                ),
              ),
              const SizedBox(width: 16),

              // Patient core details
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      patient.name,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: WhoTheme.primaryNavy,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'MRN: ${patient.mrn}  •  GA: ${patient.gestationalAgeWeeks}w  •  Age: ${ageHours}h',
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12,
                        color: Colors.grey.shade600,
                      ),
                    ),
                    if (patient.gestationalAgeWeeks < 35.0) ...[
                      const SizedBox(height: 4),
                      Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Icon(
                            Icons.warning,
                            color: WhoTheme.riskIntermediate,
                            size: 14,
                          ),
                          const SizedBox(width: 4),
                          Expanded(
                            child: const Text(
                              'Premature infant (<35 weeks)',
                              maxLines: 2,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 11,
                                color: WhoTheme.riskIntermediate,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),

              // Risk badge + AI star + chevron
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 4,
                    ),
                    decoration: BoxDecoration(
                      color: riskColor,
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      result.riskLabel,
                      style: const TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 11,
                      ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  // AI explanation star button — tap to open explanation directly
                  Tooltip(
                    message: 'AI Care Plan',
                    child: InkWell(
                      onTap: () => _openExplanation(context, ref),
                      borderRadius: BorderRadius.circular(16),
                      child: Padding(
                        padding: const EdgeInsets.all(4),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              Icons.auto_awesome,
                              size: 16,
                              color: riskColor,
                            ),
                            const SizedBox(width: 2),
                            Text(
                              'AI',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.bold,
                                color: riskColor,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 2),
                  const Icon(
                    Icons.arrow_forward_ios,
                    size: 14,
                    color: Colors.grey,
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
