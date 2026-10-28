import 'package:flutter/material.dart';
import '../../core/theme.dart';
import '../../data/api/api_client.dart';
import '../../data/offline_guideline_cache.dart';
import '../../data/offline_pdf_cache.dart';

class GuidelineConfigScreen extends StatefulWidget {
  const GuidelineConfigScreen({super.key});

  @override
  State<GuidelineConfigScreen> createState() => _GuidelineConfigScreenState();
}

class _GuidelineConfigScreenState extends State<GuidelineConfigScreen> {
  late final Future<Map<String, dynamic>> _indexStatus;
  bool _rebuilding = false;
  bool _syncing = false;
  bool _downloadingPdfs = false;
  String? _rebuildStatus;
  DateTime? _lastSynced;
  int _cachedProtocolCount = 0;
  int _pdfDownloadCompleted = 0;
  int _pdfDownloadTotal = 0;

  @override
  void initState() {
    super.initState();
    _indexStatus = apiClient.dio
        .get('/api/v1/admin/rag/health')
        .then((r) => Map<String, dynamic>.from(r.data as Map));
    _loadOfflineStatus();
  }

  Future<void> _loadOfflineStatus() async {
    final synced = await OfflineGuidelineCache.lastSynced();
    final keys = await OfflineGuidelineCache.cachedKeys();
    if (mounted) {
      setState(() {
        _lastSynced = synced;
        _cachedProtocolCount = keys.length;
      });
    }
  }

  Future<void> _rebuildVectorIndex() async {
    setState(() {
      _rebuilding = true;
      _rebuildStatus = null;
    });
    try {
      final response = await apiClient.dio.post(
        '/api/v1/admin/guidelines/ingest',
      );
      final data = response.data as Map<String, dynamic>;
      final inserted = data['chunks_inserted'] ?? 0;
      setState(
        () => _rebuildStatus =
            'Rebuilt — $inserted chunks indexed. '
            'Offline care plans will refresh next time the app syncs.',
      );
    } catch (e) {
      setState(() => _rebuildStatus = 'Rebuild failed: $e');
    } finally {
      if (mounted) setState(() => _rebuilding = false);
    }
  }

  Future<void> _syncOfflineCache() async {
    setState(() => _syncing = true);
    await OfflineGuidelineCache.sync();
    await _loadOfflineStatus();
    if (mounted) setState(() => _syncing = false);
  }

  Future<void> _downloadAllPdfs() async {
    setState(() {
      _downloadingPdfs = true;
      _pdfDownloadCompleted = 0;
      _pdfDownloadTotal = 0;
    });
    // wifiOnly: false — this is an explicit tap from Settings, not a
    // background boot sync, so the clinician has opted in to the data cost.
    await OfflinePdfCache.syncAllPdfs(
      wifiOnly: false,
      onProgress: (completed, total) {
        if (mounted) {
          setState(() {
            _pdfDownloadCompleted = completed;
            _pdfDownloadTotal = total;
          });
        }
      },
    );
    if (mounted) setState(() => _downloadingPdfs = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Guideline Configuration')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          FutureBuilder<Map<String, dynamic>>(
            future: _indexStatus,
            builder: (context, snapshot) {
              if (snapshot.hasError) {
                return const Card(
                  child: ListTile(
                    title: Text('Index status unavailable'),
                    subtitle: Text(
                      'Check the API connection and administrator permissions.',
                    ),
                  ),
                );
              }
              final data = snapshot.data;
              return Card(
                child: ListTile(
                  title: const Text('NICE NG195'),
                  subtitle: Text(
                    data == null
                        ? 'Loading actual index status…'
                        : '${data['total_chunks'] ?? 'Unknown'} passages · ${data['embedding_model'] ?? 'Encoder not reported'}\n${data['status'] ?? ''}\n${data['vector_index'] ?? ''}',
                  ),
                ),
              );
            },
          ),
          const SizedBox(height: 16),
          const Text(
            'Source ingestion',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          Container(
            height: 120,
            margin: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              border: Border.all(color: Colors.grey.shade400),
              borderRadius: BorderRadius.circular(8),
            ),
            padding: const EdgeInsets.all(16),
            child: const Center(
              child: Text(
                'Source ingestion requires administrator access and source review. New PDFs are not uploaded from this screen.',
              ),
            ),
          ),
          OutlinedButton(
            onPressed: _rebuilding
                ? null
                : _rebuildVectorIndex,
            child: _rebuilding
                ? const SizedBox(
                    height: 16,
                    width: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('Rebuild vector index'),
          ),
          if (_rebuildStatus != null) ...[
            const SizedBox(height: 8),
            Text(
              _rebuildStatus!,
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ],
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 8),
          const Text(
            'Offline care plan cache',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            'Only reviewed, available source material can be cached. A cached document does not establish an individualized care plan. '
            'When verified guidance is unavailable, the app requests clinician review.',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: Icon(
                _cachedProtocolCount > 0
                    ? Icons.offline_pin
                    : Icons.warning_amber_rounded,
                color: _cachedProtocolCount > 0
                    ? WhoTheme.riskLow
                    : WhoTheme.riskIntermediate,
              ),
              title: Text(
                '$_cachedProtocolCount protocol${_cachedProtocolCount == 1 ? '' : 's'} cached on this device',
              ),
              subtitle: Text(
                _lastSynced != null
                    ? 'Last synced: ${_lastSynced!.toLocal().toString().substring(0, 16)}'
                    : 'Never synced — connect to the backend at least once',
              ),
              trailing: TextButton(
                onPressed: _syncing ? null : _syncOfflineCache,
                child: _syncing
                    ? const SizedBox(
                        height: 16,
                        width: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Sync now'),
              ),
            ),
          ),
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 8),
          const Text(
            'Offline guideline PDFs',
            style: TextStyle(fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 4),
          Text(
            'Downloads every guideline PDF to this device so "view in source PDF" works with '
            'zero connectivity, without needing to have opened each document online first. '
            'Runs automatically over WiFi at app launch — tap below to force it now, including '
            'over mobile data.',
            style: TextStyle(fontSize: 12, color: Colors.grey.shade600),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: Icon(
                    Icons.picture_as_pdf_outlined,
                    color: WhoTheme.secondaryTeal,
                  ),
                  title: const Text('Download all guideline PDFs'),
                  subtitle: _downloadingPdfs && _pdfDownloadTotal > 0
                      ? Text(
                          'Downloading $_pdfDownloadCompleted / $_pdfDownloadTotal…',
                        )
                      : const Text('For fully offline "view in source PDF"'),
                  trailing: TextButton(
                    onPressed: _downloadingPdfs ? null : _downloadAllPdfs,
                    child: _downloadingPdfs
                        ? const SizedBox(
                            height: 16,
                            width: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('Download all'),
                  ),
                ),
                if (_downloadingPdfs && _pdfDownloadTotal > 0)
                  Padding(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
                    child: LinearProgressIndicator(
                      value: _pdfDownloadCompleted / _pdfDownloadTotal,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class AuditLogScreen extends StatelessWidget {
  const AuditLogScreen({super.key});

  Future<List<Map<String, dynamic>>> _fetchLogs() async {
    final res = await apiClient.dio.get('/api/v1/admin/audit');
    return List<Map<String, dynamic>>.from(res.data['events'] as List);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Audit Log'),
        actions: [
          IconButton(icon: const Icon(Icons.filter_list), onPressed: () {}),
          IconButton(icon: const Icon(Icons.download), onPressed: () {}),
        ],
      ),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            color: WhoTheme.riskLow.withValues(alpha: 0.2),
            child: const Text(
              'Decision provenance records. Cryptographic chain integrity is not claimed.',
            ),
          ),
          Expanded(
            child: FutureBuilder<List<Map<String, dynamic>>>(
              future: _fetchLogs(),
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasError) {
                  return Center(
                    child: Text('Error loading logs: ${snapshot.error}'),
                  );
                }
                final logs = snapshot.data ?? [];
                if (logs.isEmpty) {
                  return const Center(child: Text('No audit logs found.'));
                }
                return ListView.builder(
                  itemCount: logs.length,
                  itemBuilder: (context, index) {
                    final log = logs[index];
                    final eventType = log['operation'] ?? 'UNKNOWN';
                    final details =
                        '${log['status'] ?? ''} · ${log['model_version'] ?? ''}';
                    final createdAt = log['created_at'] != null
                        ? DateTime.tryParse(
                                log['created_at'].toString(),
                              )?.toLocal().toString().substring(0, 16) ??
                              ''
                        : '';
                    return ListTile(
                      title: Text(eventType),
                      subtitle: Text(
                        details,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: Text(createdAt),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
