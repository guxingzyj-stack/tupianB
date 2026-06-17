import 'package:go_router/go_router.dart';

import '../core/api/media_api.dart';
import '../dev/widget_demos.dart';
import '../features/enhance/pages/analyzing_page.dart';
import '../features/enhance/pages/result_page.dart';
import '../features/enhance/pages/select_photo_page.dart';
import '../features/history/pages/history_page.dart';
import '../features/home/home_page.dart';
import '../features/settings/settings_page.dart';
import '../features/template/pages/template_apply_page.dart';
import '../features/template/pages/template_list_page.dart';
import '../features/video/pages/animate_setup_page.dart';
import '../features/video/pages/video_result_page.dart';
import '../features/video/pages/waiting_page.dart';

final router = GoRouter(
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (c, s) => const HomePage()),
    GoRoute(path: '/enhance/select', builder: (c, s) => const SelectPhotoPage()),
    GoRoute(path: '/enhance/analyzing', builder: (c, s) => const AnalyzingPage()),
    GoRoute(
      path: '/enhance/result/:jobId',
      builder: (c, s) => ResultPage(jobId: s.pathParameters['jobId']!),
    ),
    // 做祝福
    GoRoute(path: '/template', builder: (c, s) => const TemplateListPage()),
    GoRoute(
      path: '/template/apply',
      builder: (c, s) => TemplateApplyPage(template: s.extra as TemplateItem),
    ),
    // 让照片动起来 / 视频
    GoRoute(
      path: '/video/animate',
      builder: (c, s) => AnimateSetupPage(imageUrl: s.extra as String),
    ),
    GoRoute(
      path: '/video/waiting',
      builder: (c, s) => WaitingPage(jobId: s.extra as String),
    ),
    GoRoute(
      path: '/video/result',
      builder: (c, s) => VideoResultPage(videoUrl: s.extra as String),
    ),
    GoRoute(path: '/history', builder: (c, s) => const HistoryPage()),
    GoRoute(path: '/settings', builder: (c, s) => const SettingsPage()),
    GoRoute(path: '/dev/widgets', builder: (c, s) => const WidgetDemosPage()),
  ],
);
