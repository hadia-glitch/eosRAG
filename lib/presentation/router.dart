import 'package:go_router/go_router.dart';
import 'screens/splash_screen.dart';
import 'screens/login_screen.dart';
import 'screens/first_login_setup_screen.dart';
import 'home_dashboard.dart';
import 'screens/new_patient_screen.dart';
import 'screens/admin_screens.dart';
import 'screens/longitudinal_inputs_screen.dart';

final appRouter = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (_, _) => const SplashScreen()),
    GoRoute(path: '/login', builder: (_, _) => const LoginScreen()),
    GoRoute(path: '/setup', builder: (_, _) => const FirstLoginSetupScreen()),
    GoRoute(path: '/home', builder: (_, _) => const HomeDashboard()),
    GoRoute(path: '/new-patient', builder: (_, _) => const NewPatientScreen()),
    GoRoute(
      path: '/research/longitudinal',
      builder: (_, _) => const LongitudinalInputsScreen(),
    ),

    // User management is intentionally parked for now.
    // GoRoute(path: '/admin/users', builder: (_, __) => const UserManagementScreen()),
    GoRoute(
      path: '/admin/guidelines',
      builder: (_, _) => const GuidelineConfigScreen(),
    ),
    GoRoute(path: '/admin/audit', builder: (_, _) => const AuditLogScreen()),
  ],
);
