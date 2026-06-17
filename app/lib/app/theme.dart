import 'package:flutter/material.dart';

/// 老照 设计系统 —— 适老化(大字/大按钮/高对比, PRD §4) + 商用级精致质感。
/// 暖色调(温暖、怀旧、可信), 渐变 + 柔和阴影 + 留白节奏。
class ElderlyTheme {
  // --- 配色 ---
  static const Color bg = Color(0xFFFBF7F0); // 暖纸白背景
  static const Color surface = Color(0xFFFFFFFF);
  static const Color ink = Color(0xFF2E2A26); // 正文 (对 bg ~11:1)
  static const Color subtle = Color(0xFF6E665C); // 辅助文字 (对 bg ~5:1)
  static const Color primary = Color(0xFFC15A2B); // 主色 暖赤陶
  static const Color secondary = Color(0xFF3E7C74); // 次色 深青
  static const Color danger = Color(0xFFB3382C);
  static const Color line = Color(0xFFE8E0D4); // 分隔/描边

  // 大卡片渐变 (白色大字 ≥3:1, 适老化大字达标)
  static const LinearGradient warmGrad = LinearGradient(
    colors: [Color(0xFFF2A65A), Color(0xFFDC6B38)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );
  static const LinearGradient tealGrad = LinearGradient(
    colors: [Color(0xFF6BA89E), Color(0xFF3E7C74)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const double radius = 20;
  static const double radiusLg = 28;

  // 柔和阴影 (层次感, 不刺眼)
  static const List<BoxShadow> shadowSoft = [
    BoxShadow(color: Color(0x1A8A5A33), blurRadius: 22, offset: Offset(0, 10)),
  ];
  static const List<BoxShadow> shadowCard = [
    BoxShadow(color: Color(0x0F463A2E), blurRadius: 14, offset: Offset(0, 5)),
  ];

  static ThemeData light({String? fontFamily}) {
    TextStyle ts(double size, FontWeight w, Color c, {double h = 1.3}) => TextStyle(
          fontFamily: fontFamily,
          fontSize: size,
          fontWeight: w,
          color: c,
          height: h,
        );

    final scheme = ColorScheme.light(
      primary: primary,
      onPrimary: Colors.white,
      secondary: secondary,
      onSecondary: Colors.white,
      surface: surface,
      onSurface: ink,
      error: danger,
      onError: Colors.white,
    );

    final textTheme = TextTheme(
      headlineLarge: ts(30, FontWeight.w800, ink, h: 1.15),
      headlineMedium: ts(26, FontWeight.w700, ink, h: 1.2),
      titleLarge: ts(22, FontWeight.w700, ink),
      titleMedium: ts(19, FontWeight.w600, ink),
      bodyLarge: ts(18, FontWeight.w400, ink, h: 1.45),
      bodyMedium: ts(16, FontWeight.w400, subtle, h: 1.4),
      labelLarge: ts(23, FontWeight.w700, Colors.white),
    );

    return ThemeData(
      useMaterial3: true,
      fontFamily: fontFamily,
      colorScheme: scheme,
      scaffoldBackgroundColor: bg,
      textTheme: textTheme,
      // 主按钮: 高度≥64, 圆角20, 字23粗, 带暖色投影 (PRD §4.2)
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          minimumSize: const Size.fromHeight(64),
          backgroundColor: primary,
          foregroundColor: Colors.white,
          textStyle: ts(23, FontWeight.w700, Colors.white),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
          elevation: 3,
          shadowColor: const Color(0x4DC15A2B),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(64),
          foregroundColor: ink,
          backgroundColor: surface,
          textStyle: ts(22, FontWeight.w700, ink),
          side: const BorderSide(color: line, width: 1.5),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(radius)),
        ),
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: bg,
        foregroundColor: ink,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: ts(22, FontWeight.w700, ink),
        iconTheme: const IconThemeData(size: 30, color: ink),
      ),
    );
  }
}
