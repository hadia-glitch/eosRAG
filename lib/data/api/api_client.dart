import 'dart:developer' as developer;
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import '../auth_service.dart';
import '../supabase_config.dart';

class ApiClient {
  /// URL resolution order:
  ///   1. API_BASE_URL set in the .env file at the project root — set this
  ///      to your LAN IP for a physical device, e.g.
  ///      API_BASE_URL=http://192.168.x.x:8000
  ///   2. Android (emulator): http://10.0.2.2:8000
  ///   3. iOS simulator / desktop: http://127.0.0.1:8000
  static String get _resolvedBaseUrl {
    final defined = dotenv.env['API_BASE_URL']?.trim() ?? '';
    if (defined.isNotEmpty) return defined;
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000'; // emulator host alias only
    }
    return 'http://127.0.0.1:8000';
  }

  late final Dio _dio;
  final String baseUrl;

  ApiClient({String? baseUrl}) : baseUrl = baseUrl ?? _resolvedBaseUrl {
    _dio = Dio(
      BaseOptions(
        baseUrl: this.baseUrl,
        connectTimeout: const Duration(seconds: 10),
        // Bounded generation and parallel verification fit within this deadline.
        receiveTimeout: const Duration(seconds: 90),
        headers: {'Content-Type': 'application/json'},
      ),
    );
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) {
          if (SupabaseConfig.isConfigured) {
            final token =
                AuthService.instance.client.auth.currentSession?.accessToken;
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          }
          handler.next(options);
        },
      ),
    );
    if (kDebugMode) {
      _dio.interceptors.add(
        LogInterceptor(
          requestBody: false,
          responseBody: false,
          requestHeader: false,
          responseHeader: false,
          logPrint: (o) => developer.log('$o', name: 'Dio'),
        ),
      );
    }
  }

  Dio get dio => _dio;

  Future<bool> isBackendAvailable() async {
    try {
      final response = await _dio.get(
        '/health',
        options: Options(
          sendTimeout: const Duration(seconds: 5),
          receiveTimeout: const Duration(seconds: 5),
        ),
      );
      final ok = response.statusCode == 200;
      developer.log(
        '[ApiClient] health=$ok baseUrl=$baseUrl',
        name: 'ApiClient',
      );
      return ok;
    } catch (e) {
      developer.log(
        '[ApiClient] unreachable at $baseUrl — $e',
        name: 'ApiClient',
      );
      return false;
    }
  }
}

final apiClient = ApiClient();
