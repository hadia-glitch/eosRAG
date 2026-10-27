import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'core/theme.dart';
import 'data/supabase_config.dart';
import 'presentation/router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Only public build configuration enters the client bundle. Never bundle
  // the developer's .env, which may also contain server credentials.
  dotenv.testLoad(
    fileInput:
        'API_BASE_URL=${const String.fromEnvironment('API_BASE_URL')}\nSUPABASE_URL=${const String.fromEnvironment('SUPABASE_URL')}\nSUPABASE_ANON_KEY=${const String.fromEnvironment('SUPABASE_ANON_KEY')}',
  );

  final supabaseConfig = await SupabaseConfig.load();
  if (supabaseConfig != null && supabaseConfig.isConfigured) {
    await Supabase.initialize(
      url: supabaseConfig.url,
      publishableKey: supabaseConfig.anonKey,
    );
  }
  runApp(const ProviderScope(child: NeoGuardApp()));
}

class NeoGuardApp extends StatelessWidget {
  const NeoGuardApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'NeoGuard AI CDSS',
      debugShowCheckedModeBanner: false,
      theme: WhoTheme.lightTheme,
      routerConfig: appRouter,
    );
  }
}
