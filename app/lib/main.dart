import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/router.dart';
import 'app/theme.dart';

void main() {
  runApp(const ProviderScope(child: LaozhaoApp()));
}

class LaozhaoApp extends StatelessWidget {
  const LaozhaoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: '老照',
      debugShowCheckedModeBanner: false,
      theme: ElderlyTheme.light(),
      routerConfig: router,
    );
  }
}
