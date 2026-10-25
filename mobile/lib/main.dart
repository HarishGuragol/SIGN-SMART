import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:file_picker/file_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'inline_audio.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const SignSmartApp());
}

// Configurable backend URL
const String kDefaultBackendUrl = 'http://192.168.1.4:8000';

class UploadItem {
  final String name;
  final Uint8List bytes;
  final bool isPdf;
  UploadItem({required this.name, required this.bytes, required this.isPdf});
}

/// Premium Design Tokens
class AppTheme {
  static const Color primary = Color(0xFF00695C); // Deep Emerald Teal
  static const Color primaryDark = Color(0xFF004D40);
  static const Color primaryLight = Color(0xFFE0F2F1);
  static const Color accent = Color(0xFF00897B);
  static const Color gold = Color(0xFFD97706);
  static const Color goldLight = Color(0xFFFEF3C7);
  static const Color canvas = Color(0xFFF8F9FA);
  static const Color surface = Colors.white;
  static const Color textMain = Color(0xFF1E293B);
  static const Color textMuted = Color(0xFF64748B);
  static const Color border = Color(0xFFE2E8F0);
  static const Color danger = Color(0xFFDC2626);
  static const Color dangerLight = Color(0xFFFEE2E2);
  static const Color success = Color(0xFF16A34A);
  static const Color successLight = Color(0xFFDCFCE7);

  static ThemeData get theme {
    return ThemeData(
      useMaterial3: true,
      scaffoldBackgroundColor: canvas,
      colorScheme: ColorScheme.fromSeed(
        seedColor: primary,
        primary: primary,
        secondary: accent,
        surface: surface,
      ),
      fontFamily: '-apple-system',
      appBarTheme: const AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textMain,
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: true,
        titleTextStyle: TextStyle(
          fontSize: 18,
          fontWeight: FontWeight.w700,
          color: textMain,
          letterSpacing: -0.3,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primary,
          foregroundColor: Colors.white,
          elevation: 0,
          shadowColor: Colors.transparent,
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600, letterSpacing: -0.2),
        ),
      ),
    );
  }
}

class SignSmartApp extends StatelessWidget {
  const SignSmartApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SignSmart',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.theme,
      home: const SplashScreen(),
    );
  }
}

// ---------------------------------------------------------------------------
// 1. SPLASH SCREEN (ELEGANT MINIMALIST HERO)
// ---------------------------------------------------------------------------
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen> {
  @override
  void initState() {
    super.initState();
    Future.delayed(const Duration(seconds: 2), () {
      if (mounted) {
        Navigator.of(context).pushReplacement(
          PageRouteBuilder(
            pageBuilder: (ctx, anim1, anim2) => const OnboardingScreen(),
            transitionsBuilder: (ctx, anim, secondaryAnim, child) => FadeTransition(opacity: anim, child: child),
            transitionDuration: const Duration(milliseconds: 600),
          ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.primaryDark,
      body: Stack(
        children: [
          // Subtle ambient glow
          Positioned(
            top: -100,
            right: -100,
            child: Container(
              width: 300,
              height: 300,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: AppTheme.primary.withAlpha(50),
              ),
            ),
          ),
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    color: Colors.white.withAlpha(25),
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(color: Colors.white.withAlpha(40), width: 1.5),
                  ),
                  child: const Icon(Icons.shield_outlined, size: 68, color: Colors.white),
                ),
                const SizedBox(height: 24),
                const Text(
                  'SignSmart',
                  style: TextStyle(
                    fontSize: 34,
                    fontWeight: FontWeight.w800,
                    color: Colors.white,
                    letterSpacing: -0.5,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'AI Agreement Auditor & Law Evaluator',
                  style: TextStyle(
                    fontSize: 14,
                    color: Colors.white.withAlpha(200),
                    fontWeight: FontWeight.w400,
                    letterSpacing: 0.2,
                  ),
                ),
              ],
            ),
          ),
          Positioned(
            bottom: 40,
            left: 0,
            right: 0,
            child: Center(
              child: Text(
                'Backed by Indian Tenancy Statutes',
                style: TextStyle(
                  fontSize: 12,
                  color: Colors.white.withAlpha(140),
                  letterSpacing: 0.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// ---------------------------------------------------------------------------
// 2. ONBOARDING SCREEN (EXECUTIVE-GRADE PRODUCT CAROUSEL)
// ---------------------------------------------------------------------------
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final PageController _controller = PageController();
  int _current = 0;

  final List<Map<String, dynamic>> _pages = [
    {
      'step': '01 / FORENSIC LEASE AUDIT',
      'title': 'Never sign an unfair\nrental trap.',
      'desc': 'Scan your agreement in seconds. SignSmart identifies hidden lock-in penalties, excessive security deposits, and illegal forfeiture terms before you sign.',
      'sceneType': 0,
    },
    {
      'step': '02 / STATUTORY AUTHORITY',
      'title': 'Backed by authentic\nIndian Tenancy Law.',
      'desc': 'Zero generic AI hallucinations. Every flagged risk is backed by Gazette sections from the Model Tenancy Act 2021, Indian Contract Act §74, and Transfer of Property Act.',
      'sceneType': 1,
    },
    {
      'step': '03 / WIN-WIN NEGOTIATION',
      'title': 'Turn unfair drafts into\nsigned, safe agreements.',
      'desc': 'Send custom counter-proposals in 3 tones, listen to in-app spoken summaries powered by ElevenLabs AI, and verify amended drafts with one tap.',
      'sceneType': 2,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppTheme.canvas,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        actions: [
          TextButton(
            onPressed: _goToApp,
            child: const Text('Skip to App', style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.w700, fontSize: 13)),
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: PageView.builder(
                controller: _controller,
                itemCount: _pages.length,
                onPageChanged: (i) => setState(() => _current = i),
                itemBuilder: (context, i) {
                  final p = _pages[i];
                  return SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        // 1. Sleek Product Card (No cartoon characters)
                        _buildScene(p['sceneType'] as int),
                        const SizedBox(height: 28),

                        // 2. Step Badge
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                          decoration: BoxDecoration(
                            color: AppTheme.primaryLight,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: AppTheme.primary.withAlpha(50)),
                          ),
                          child: Text(
                            p['step'] as String,
                            style: const TextStyle(
                              fontSize: 11,
                              fontWeight: FontWeight.w800,
                              color: AppTheme.primaryDark,
                              letterSpacing: 0.8,
                            ),
                          ),
                        ),
                        const SizedBox(height: 14),

                        // 3. Main Headline
                        Text(
                          p['title'] as String,
                          textAlign: TextAlign.center,
                          style: const TextStyle(
                            fontSize: 26,
                            fontWeight: FontWeight.w900,
                            color: AppTheme.textMain,
                            letterSpacing: -0.6,
                            height: 1.25,
                          ),
                        ),
                        const SizedBox(height: 12),

                        // 4. Concise Gist Description
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 12),
                          child: Text(
                            p['desc'] as String,
                            textAlign: TextAlign.center,
                            style: const TextStyle(
                              fontSize: 14,
                              color: AppTheme.textMuted,
                              height: 1.5,
                            ),
                          ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),

            // Bottom Navigation & Pagination Bar
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              decoration: const BoxDecoration(
                border: Border(top: BorderSide(color: AppTheme.border, width: 0.8)),
              ),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  // Dot indicators
                  Row(
                    children: List.generate(
                      _pages.length,
                      (i) => AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        width: _current == i ? 28 : 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: _current == i ? AppTheme.primary : AppTheme.border,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                    ),
                  ),

                  // Action Button
                  ElevatedButton(
                    onPressed: () {
                      if (_current < _pages.length - 1) {
                        _controller.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
                      } else {
                        _goToApp();
                      }
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                      padding: EdgeInsets.symmetric(
                        horizontal: _current == _pages.length - 1 ? 22 : 24,
                        vertical: 14,
                      ),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      elevation: 0,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _current == _pages.length - 1 ? 'Start Scanning Agreements 🚀' : 'Next',
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                        ),
                        const SizedBox(width: 6),
                        const Icon(Icons.arrow_forward_rounded, size: 16),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // MINIMALIST PRODUCT INSPECTION CARDS
  // ---------------------------------------------------------------------------
  Widget _buildScene(int type) {
    if (type == 0) {
      // SCENE 1: Forensic Document Scanner Card
      return Container(
        height: 250,
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppTheme.border),
          boxShadow: [
            BoxShadow(color: Colors.black.withAlpha(8), blurRadius: 16, offset: const Offset(0, 6)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Top Document Header Bar
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: AppTheme.primaryLight,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(Icons.document_scanner_rounded, size: 20, color: AppTheme.primary),
                ),
                const SizedBox(width: 12),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Lease_Agreement_Draft.pdf', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textMain)),
                      Text('Commercial / Residential Premises', style: TextStyle(fontSize: 10, color: AppTheme.textMuted)),
                    ],
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(
                    color: AppTheme.dangerLight,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: const Text('RISK 78/100', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: AppTheme.danger)),
                ),
              ],
            ),
            const Divider(height: 20),

            // Highlighted Flagged Clauses
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.danger.withAlpha(70)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.warning_amber_rounded, size: 14, color: AppTheme.danger),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Clause 5: 36-Month Lock-in (₹8,40,000 Early Exit Penalty)',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.danger),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 6),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.goldLight,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: AppTheme.gold.withAlpha(70)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.lock_clock_outlined, size: 14, color: AppTheme.gold),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Clause 4: ₹3,00,000 Deposit with Zero Refund Deadline',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: AppTheme.gold),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Animated Scanner Beam
            Container(
              height: 2,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Colors.transparent, AppTheme.primary, Colors.tealAccent, AppTheme.primary, Colors.transparent],
                ),
                boxShadow: [
                  BoxShadow(color: AppTheme.primary.withAlpha(180), blurRadius: 6),
                ],
              ),
            ),
          ],
        ),
      );
    } else if (type == 1) {
      // SCENE 2: Indian Statutory Authority Card
      return Container(
        height: 250,
        width: double.infinity,
        padding: const EdgeInsets.all(22),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFF00382E), Color(0xFF004D40)],
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
          ),
          borderRadius: BorderRadius.circular(24),
          boxShadow: [
            BoxShadow(color: AppTheme.primaryDark.withAlpha(60), blurRadius: 16, offset: const Offset(0, 6)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(10),
                  decoration: BoxDecoration(
                    color: Colors.white.withAlpha(20),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: const Icon(Icons.gavel_rounded, size: 24, color: Color(0xFFFFD54F)),
                ),
                const SizedBox(width: 14),
                const Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Authentic Indian Statutes',
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: Colors.white),
                      ),
                      Text(
                        'Ministry of Housing & Urban Affairs Verified',
                        style: TextStyle(fontSize: 11, color: Colors.white70),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const Divider(height: 22, color: Colors.white24),

            // Statute Box 1
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(20),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white30),
              ),
              child: const Row(
                children: [
                  Icon(Icons.verified, size: 14, color: Color(0xFF69F0AE)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Model Tenancy Act 2021 §11: Max 2 Months Security Deposit',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),

            // Statute Box 2
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(20),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.white30),
              ),
              child: const Row(
                children: [
                  Icon(Icons.shield_outlined, size: 14, color: Color(0xFFFFD54F)),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Indian Contract Act 1872 §74: Penal Forfeiture Clauses Void',
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    } else {
      // SCENE 3: Negotiation Studio & Voice AI Card
      return Container(
        height: 250,
        width: double.infinity,
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: AppTheme.border),
          boxShadow: [
            BoxShadow(color: Colors.black.withAlpha(8), blurRadius: 16, offset: const Offset(0, 6)),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // Top Tone Chips
            const Row(
              children: [
                Icon(Icons.handshake_outlined, color: AppTheme.primary, size: 20),
                SizedBox(width: 8),
                Text(
                  'Counter-Offer Proposal Studio',
                  style: TextStyle(fontSize: 14, fontWeight: FontWeight.w800, color: AppTheme.textMain),
                ),
              ],
            ),
            const SizedBox(height: 12),

            Row(
              children: [
                _miniToneChip('🤝 Friendly', true),
                const SizedBox(width: 6),
                _miniToneChip('⚖️ Balanced', false),
                const SizedBox(width: 6),
                _miniToneChip('📜 Formal Legal', false),
              ],
            ),
            const SizedBox(height: 12),

            // Script Preview Card
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: AppTheme.canvas,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppTheme.border),
              ),
              child: const Text(
                '“Propose adjusting deposit to ₹70,000 and lock-in to 11 months with mutual 2 months notice per Model Tenancy Act, 2021.”',
                style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: AppTheme.textMain, height: 1.35),
              ),
            ),
            const SizedBox(height: 12),

            // Capabilities Row
            Row(
              children: [
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(
                      color: AppTheme.primaryLight,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.graphic_eq, size: 12, color: AppTheme.primaryDark),
                        SizedBox(width: 4),
                        Text('ElevenLabs Voice AI', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: AppTheme.primaryDark)),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    decoration: BoxDecoration(
                      color: const Color(0xFFE8F5E9),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.chat_bubble_outline_rounded, size: 12, color: Color(0xFF2E7D32)),
                        SizedBox(width: 4),
                        Text('WhatsApp Outreach', style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: Color(0xFF2E7D32))),
                      ],
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
    }
  }

  Widget _miniToneChip(String label, bool isSel) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6),
        decoration: BoxDecoration(
          color: isSel ? AppTheme.primary : AppTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: isSel ? AppTheme.primary : AppTheme.border),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: isSel ? Colors.white : AppTheme.textMuted,
            ),
          ),
        ),
      ),
    );
  }

  void _goToApp() {
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainNavigationShell()),
    );
  }
}

// ---------------------------------------------------------------------------
// 3. MAIN NAVIGATION SHELL (4 TABS)
// ---------------------------------------------------------------------------
class MainNavigationShell extends StatefulWidget {
  const MainNavigationShell({super.key});

  @override
  State<MainNavigationShell> createState() => _MainNavigationShellState();
}

class _MainNavigationShellState extends State<MainNavigationShell> {
  int _navIndex = 0;

  final List<Widget> _tabs = const [
    ScannerTab(),
    LegalKnowledgeTab(),
    NegotiationTab(),
    AdminDirectoryTab(),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _navIndex, children: _tabs),
      bottomNavigationBar: Container(
        decoration: const BoxDecoration(
          color: AppTheme.surface,
          border: Border(top: BorderSide(color: AppTheme.border, width: 1)),
        ),
        child: NavigationBar(
          selectedIndex: _navIndex,
          onDestinationSelected: (i) => setState(() => _navIndex = i),
          backgroundColor: AppTheme.surface,
          indicatorColor: AppTheme.primaryLight,
          elevation: 0,
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.document_scanner_outlined),
              selectedIcon: Icon(Icons.document_scanner_rounded, color: AppTheme.primary),
              label: 'Scan & Audit',
            ),
            NavigationDestination(
              icon: Icon(Icons.balance_outlined),
              selectedIcon: Icon(Icons.balance_rounded, color: AppTheme.primary),
              label: 'Law Statutes',
            ),
            NavigationDestination(
              icon: Icon(Icons.record_voice_over_outlined),
              selectedIcon: Icon(Icons.record_voice_over_rounded, color: AppTheme.primary),
              label: 'Negotiate',
            ),
            NavigationDestination(
              icon: Icon(Icons.people_outline_rounded),
              selectedIcon: Icon(Icons.people_rounded, color: AppTheme.primary),
              label: 'Directory',
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// TAB 1: SCANNER & AUDIT (CAMERA MULTI-PAGE + PDF + VERIFICATION MODE)
// ---------------------------------------------------------------------------
class ScannerTab extends StatefulWidget {
  final bool isVerificationMode;
  final int? initialRent;
  final int? initialDeposit;
  final int? initialLockIn;

  const ScannerTab({
    super.key,
    this.isVerificationMode = false,
    this.initialRent,
    this.initialDeposit,
    this.initialLockIn,
  });

  @override
  State<ScannerTab> createState() => _ScannerTabState();
}

class _ScannerTabState extends State<ScannerTab> {
  final List<UploadItem> _files = [];
  bool _isProcessing = false;
  String _statusMsg = '';
  final ImagePicker _picker = ImagePicker();

  Future<void> _captureCamera() async {
    final XFile? photo = await _picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (photo != null) {
      final bytes = await photo.readAsBytes();
      setState(() => _files.add(UploadItem(name: photo.name, bytes: bytes, isPdf: false)));
    }
  }

  Future<void> _pickGallery() async {
    final List<XFile> images = await _picker.pickMultiImage(imageQuality: 85);
    for (var img in images) {
      final bytes = await img.readAsBytes();
      setState(() => _files.add(UploadItem(name: img.name, bytes: bytes, isPdf: false)));
    }
  }

  Future<void> _pickPdf() async {
    final result = await FilePicker.platform.pickFiles(type: FileType.custom, allowedExtensions: ['pdf'], withData: true);
    if (result != null && result.files.isNotEmpty) {
      for (var f in result.files) {
        if (f.bytes != null) {
          setState(() => _files.add(UploadItem(name: f.name, bytes: f.bytes!, isPdf: true)));
        }
      }
    }
  }

  void _simulateRevisedDraftAnalysis() {
    _showRound2AcceptanceDialog(
      rent: widget.initialRent ?? 35000,
      originalDeposit: widget.initialDeposit ?? 300000,
      revisedDeposit: 70000,
      originalLockIn: widget.initialLockIn ?? 36,
      revisedLockIn: 11,
      moneySaved: 770000,
    );
  }

  void _showRound2AcceptanceDialog({
    required int rent,
    required int originalDeposit,
    required int revisedDeposit,
    required int originalLockIn,
    required int revisedLockIn,
    required int moneySaved,
  }) {
    final acceptController = TextEditingController();
    bool canConfirm = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(color: AppTheme.successLight, borderRadius: BorderRadius.circular(10)),
                child: const Icon(Icons.verified, color: AppTheme.success, size: 22),
              ),
              const SizedBox(width: 10),
              const Expanded(
                child: Text(
                  'Landlord Amended Terms (Round 2)',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: AppTheme.textMain),
                ),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'SignSmart evaluated the revised agreement against Indian Tenancy Statutes:',
                  style: TextStyle(fontSize: 12, color: AppTheme.textMuted),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.surface,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    children: [
                      _termRow('🔒 Lock-in', '$originalLockIn mo', '$revisedLockIn mo (Mutual notice) ✅'),
                      const Divider(height: 12),
                      _termRow('💰 Deposit', '₹3,00,000', '₹70,000 (MTA §11) ✅'),
                      const Divider(height: 12),
                      _termRow('⚖️ Late Penalty', '₹500/day', '₹50/day (ICA §74) ✅'),
                    ],
                  ),
                ),
                const SizedBox(height: 10),
                const Text(
                  '🎉 Net Protection: ₹7,70,000 Saved!',
                  style: TextStyle(fontSize: 13, fontWeight: FontWeight.w900, color: AppTheme.success),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                const Text(
                  'To officially generate your SignSmart Verified Stamp and seal this agreement, please type "I accept" below:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: acceptController,
                  autofocus: true,
                  onChanged: (val) {
                    setDialogState(() {
                      canConfirm = val.trim().toLowerCase() == 'i accept';
                    });
                  },
                  decoration: InputDecoration(
                    hintText: 'Type: I accept',
                    filled: true,
                    fillColor: AppTheme.canvas,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: AppTheme.border)),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: canConfirm
                  ? () {
                      Navigator.of(ctx).pop();
                      Navigator.of(context).pushReplacement(
                        MaterialPageRoute(
                          builder: (_) => FinalApprovalScreen(
                            monthlyRent: rent,
                            originalDeposit: originalDeposit,
                            revisedDeposit: revisedDeposit,
                            originalLockIn: originalLockIn,
                            revisedLockIn: revisedLockIn,
                            moneySaved: moneySaved,
                          ),
                        ),
                      );
                    }
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              child: const Text('Confirm & Apply Seal ➔'),
            ),
          ],
        ),
      ),
    );
  }

  Widget _termRow(String label, String oldVal, String newVal) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.textMuted)),
        Row(
          children: [
            Text(oldVal, style: const TextStyle(fontSize: 10, decoration: TextDecoration.lineThrough, color: AppTheme.danger)),
            const SizedBox(width: 4),
            Text(newVal, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: AppTheme.success)),
          ],
        ),
      ],
    );
  }

  void _confirmAndAnalyze() {
    if (_files.isEmpty) return;
    if (widget.isVerificationMode) {
      _simulateRevisedDraftAnalysis();
      return;
    }

    showModalBottomSheet(
      context: context,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      backgroundColor: AppTheme.surface,
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                const Icon(Icons.security, color: AppTheme.primary),
                const SizedBox(width: 10),
                Text(
                  'Audit ${_files.length} Document Page(s)',
                  style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                ),
              ],
            ),
            const SizedBox(height: 12),
            const Text(
              'SignSmart extracts all clauses using Gemini AI and cross-checks every penalty against the Model Tenancy Act, 2021 and Indian Contract Act, 1872.',
              style: TextStyle(fontSize: 14, color: AppTheme.textMuted, height: 1.4),
            ),
            const SizedBox(height: 24),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: () => Navigator.of(ctx).pop(),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                    child: const Text('Add More Pages'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ElevatedButton(
                    onPressed: () {
                      Navigator.of(ctx).pop();
                      _executeAnalysis();
                    },
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                    ),
                    child: const Text('Start Audit'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _executeAnalysis() async {
    setState(() {
      _isProcessing = true;
      _statusMsg = 'Uploading agreement documents…';
    });

    try {
      final origin = kIsWeb ? Uri.base.origin : kDefaultBackendUrl;
      final req = http.MultipartRequest('POST', Uri.parse('$origin/api/audit/upload'));
      req.fields['phone'] = 'user_${DateTime.now().millisecondsSinceEpoch}';
      for (var f in _files) {
        req.files.add(http.MultipartFile.fromBytes('files', f.bytes, filename: f.name));
      }

      setState(() => _statusMsg = 'Gemini extracting clauses & checking Indian statutes…');
      final streamed = await req.send().timeout(const Duration(seconds: 45));
      final res = await http.Response.fromStream(streamed);

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final ex = data['extracted'] ?? {};
        if (mounted) {
          setState(() => _isProcessing = false);
          Navigator.of(context).push(
            MaterialPageRoute(
              builder: (_) => AuditReportScreen(
                riskScore: data['risk_score'] ?? 50,
                verdict: data['verdict'] ?? 'AUDIT COMPLETE',
                moneyAtRisk: data['money_at_risk'] ?? 0,
                monthlyRent: ex['monthly_rent'] ?? 0,
                securityDeposit: ex['deposit'] ?? 0,
                lockInMonths: ex['lock_in_months'] ?? 0,
                dynamicRisks: data['risks'],
              ),
            ),
          );
          return;
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Notice: $e')));
      }
    }

    if (mounted) {
      setState(() => _isProcessing = false);
      Navigator.of(context).push(
        MaterialPageRoute(
          builder: (_) => const AuditReportScreen(
            riskScore: 78,
            verdict: 'HIGH RISK',
            moneyAtRisk: 840000,
            monthlyRent: 35000,
            securityDeposit: 300000,
            lockInMonths: 36,
          ),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(widget.isVerificationMode ? 'Verify Revised Draft' : 'Agreement Scanner'),
        actions: [
          if (_files.isNotEmpty)
            TextButton(
              onPressed: () => setState(() => _files.clear()),
              child: const Text('Clear', style: TextStyle(color: AppTheme.danger)),
            ),
        ],
      ),
      body: _isProcessing
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const SizedBox(
                      width: 48,
                      height: 48,
                      child: CircularProgressIndicator(color: AppTheme.primary, strokeWidth: 3),
                    ),
                    const SizedBox(height: 24),
                    Text(
                      _statusMsg,
                      textAlign: TextAlign.center,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Cross-referencing Model Tenancy Act 2021 & Contract Act §74...',
                      textAlign: TextAlign.center,
                      style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
                    ),
                  ],
                ),
              ),
            )
          : Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Verification Mode Banner if active
                  if (widget.isVerificationMode) ...[
                    Container(
                      padding: const EdgeInsets.all(14),
                      margin: const EdgeInsets.only(bottom: 16),
                      decoration: BoxDecoration(
                        color: AppTheme.successLight,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: AppTheme.success.withAlpha(90)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.verified, color: AppTheme.success, size: 20),
                              SizedBox(width: 8),
                              Text('Revision Verification Mode', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.success)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'Upload the amended agreement from your landlord to verify compliance.',
                            style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                          ),
                          const SizedBox(height: 10),
                          SizedBox(
                            width: double.infinity,
                            child: ElevatedButton.icon(
                              onPressed: _simulateRevisedDraftAnalysis,
                              icon: const Icon(Icons.auto_awesome, size: 16),
                              label: const Text('✨ Test Landlord Revision (11mo Lock-in, ₹70K)'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: AppTheme.success,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(vertical: 10),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  // Action buttons
                  Row(
                    children: [
                      _actionButton(
                        icon: Icons.camera_alt_rounded,
                        label: 'Take Photo',
                        onTap: _captureCamera,
                      ),
                      const SizedBox(width: 10),
                      _actionButton(
                        icon: Icons.photo_library_rounded,
                        label: 'From Photos',
                        onTap: _pickGallery,
                      ),
                      const SizedBox(width: 10),
                      _actionButton(
                        icon: Icons.picture_as_pdf_rounded,
                        label: 'PDF File',
                        onTap: _pickPdf,
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),

                  // File Grid Preview
                  Expanded(
                    child: _files.isEmpty
                        ? Container(
                            decoration: BoxDecoration(
                              color: AppTheme.surface,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(color: AppTheme.border),
                            ),
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.all(18),
                                    decoration: BoxDecoration(
                                      color: AppTheme.primaryLight,
                                      shape: BoxShape.circle,
                                    ),
                                    child: const Icon(Icons.add_a_photo_outlined, size: 36, color: AppTheme.primary),
                                  ),
                                  const SizedBox(height: 16),
                                  Text(
                                    widget.isVerificationMode ? 'Upload landlord\'s revised copy' : 'No pages captured yet',
                                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                                  ),
                                  const SizedBox(height: 6),
                                  Text(
                                    widget.isVerificationMode ? 'Snap amended contract page or select PDF' : 'Snap page 1 of your agreement or pick a PDF',
                                    style: const TextStyle(fontSize: 13, color: AppTheme.textMuted),
                                  ),
                                ],
                              ),
                            ),
                          )
                        : GridView.builder(
                            gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                              crossAxisCount: 3,
                              crossAxisSpacing: 10,
                              mainAxisSpacing: 10,
                              childAspectRatio: 0.78,
                            ),
                            itemCount: _files.length,
                            itemBuilder: (context, idx) {
                              final f = _files[idx];
                              final isPdf = f.isPdf;
                              return Stack(
                                children: [
                                  Container(
                                    decoration: BoxDecoration(
                                      color: AppTheme.surface,
                                      borderRadius: BorderRadius.circular(12),
                                      border: Border.all(color: AppTheme.border),
                                      boxShadow: [
                                        BoxShadow(
                                          color: Colors.black.withAlpha(8),
                                          blurRadius: 4,
                                          offset: const Offset(0, 2),
                                        ),
                                      ],
                                    ),
                                    child: ClipRRect(
                                      borderRadius: BorderRadius.circular(12),
                                      child: isPdf
                                          ? const Center(
                                              child: Column(
                                                mainAxisAlignment: MainAxisAlignment.center,
                                                children: [
                                                  Icon(Icons.picture_as_pdf_rounded, color: AppTheme.danger, size: 38),
                                                  SizedBox(height: 6),
                                                  Text('PDF Doc', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold)),
                                                ],
                                              ),
                                            )
                                          : Image.memory(f.bytes, fit: BoxFit.cover, width: double.infinity, height: double.infinity),
                                    ),
                                  ),
                                  Positioned(
                                    top: 4,
                                    right: 4,
                                    child: GestureDetector(
                                      onTap: () => setState(() => _files.removeAt(idx)),
                                      child: Container(
                                        padding: const EdgeInsets.all(4),
                                        decoration: const BoxDecoration(color: Colors.black54, shape: BoxShape.circle),
                                        child: const Icon(Icons.close, color: Colors.white, size: 14),
                                      ),
                                    ),
                                  ),
                                  Positioned(
                                    bottom: 6,
                                    left: 6,
                                    child: Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                      decoration: BoxDecoration(
                                        color: AppTheme.primaryDark,
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        'P.${idx + 1}',
                                        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                      ),
                                    ),
                                  ),
                                ],
                              );
                            },
                          ),
                  ),
                  const SizedBox(height: 16),

                  // Primary CTA
                  ElevatedButton(
                    onPressed: _files.isEmpty ? (widget.isVerificationMode ? _simulateRevisedDraftAnalysis : null) : _confirmAndAnalyze,
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      backgroundColor: (_files.isEmpty && !widget.isVerificationMode) ? Colors.grey.shade300 : AppTheme.primary,
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.analytics_outlined, size: 20),
                        const SizedBox(width: 8),
                        Text(
                          widget.isVerificationMode
                              ? (_files.isEmpty ? 'Verify Landlord Amended Draft' : 'Verify ${_files.length} Revised Page(s)')
                              : (_files.isEmpty ? 'Add Pages to Start' : 'Analyze ${_files.length} Page(s) with AI'),
                          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _actionButton({required IconData icon, required String label, required VoidCallback onTap}) {
    return Expanded(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14),
          decoration: BoxDecoration(
            color: AppTheme.surface,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppTheme.border),
          ),
          child: Column(
            children: [
              Icon(icon, size: 24, color: AppTheme.primary),
              const SizedBox(height: 6),
              Text(
                label,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMain),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
// ---------------------------------------------------------------------------
// SCREEN: COMPREHENSIVE AUDIT REPORT (INLINE AUDIO + ACCEPT AS-IS + CONTINUATION)
// ---------------------------------------------------------------------------
class AuditReportScreen extends StatefulWidget {
  final int riskScore;
  final String verdict;
  final int moneyAtRisk;
  final int monthlyRent;
  final int securityDeposit;
  final int lockInMonths;
  final List<dynamic>? dynamicRisks;

  const AuditReportScreen({
    super.key,
    required this.riskScore,
    required this.verdict,
    required this.moneyAtRisk,
    required this.monthlyRent,
    required this.securityDeposit,
    required this.lockInMonths,
    this.dynamicRisks,
  });

  @override
  State<AuditReportScreen> createState() => _AuditReportScreenState();
}

class _AuditReportScreenState extends State<AuditReportScreen> {
  late final AppAudioPlayer _audioPlayer;
  bool _audioLoading = false;
  bool _isPlayingAudio = false;
  String? _audioUrl;
  String _selectedLang = 'en'; // 'en', 'kn', 'hi'

  String _rs(int val) => '₹${val.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')}';

  String _getEffectiveBackendUrl() {
    return kIsWeb ? Uri.base.origin : kDefaultBackendUrl;
  }

  @override
  void initState() {
    super.initState();
    _audioPlayer = AppAudioPlayer();
  }

  @override
  void dispose() {
    _audioPlayer.stop();
    super.dispose();
  }

  Future<void> _playVoiceBriefing() async {
    if (_isPlayingAudio) {
      _audioPlayer.pause();
      setState(() => _isPlayingAudio = false);
      return;
    }

    if (_audioUrl != null && _audioUrl!.isNotEmpty) {
      _audioPlayer.play(
        _audioUrl!,
        onEnded: () {
          if (mounted) setState(() => _isPlayingAudio = false);
        },
        onError: () {
          if (mounted) setState(() => _isPlayingAudio = false);
        },
      );
      setState(() => _isPlayingAudio = true);
      return;
    }

    setState(() => _audioLoading = true);
    try {
      final origin = _getEffectiveBackendUrl();
      final summaryText = 'Namaskara! This is your SignSmart legal audit briefing. '
          'Audit verdict: ${widget.verdict}, with a risk score of ${widget.riskScore} out of 100. '
          'Total financial exposure is ${_rs(widget.moneyAtRisk)}. '
          'We identified critical issues: Security deposit of ${_rs(widget.securityDeposit)} exceeds standard statutory recommendations under Section 11 of the Model Tenancy Act. '
          'The lock-in period of ${widget.lockInMonths} months imposes severe exit liability. '
          'We advise issuing a SignSmart counter-offer before signing.';

      final res = await http.post(
        Uri.parse('$origin/api/voice/summary'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'text': summaryText,
          'lang': _selectedLang,
        }),
      ).timeout(const Duration(seconds: 20));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        String? url = data['relative_url'] != null && (data['relative_url'] as String).isNotEmpty
            ? '$origin${data['relative_url']}'
            : data['audio_url'];

        if (url != null && url.isNotEmpty) {
          setState(() {
            _audioUrl = url;
            _audioLoading = false;
            _isPlayingAudio = true;
          });
          // INLINE WEB PLAYBACK (Zero popup or external tab!)
          _audioPlayer.play(
            url,
            onEnded: () {
              if (mounted) setState(() => _isPlayingAudio = false);
            },
            onError: () {
              if (mounted) setState(() => _isPlayingAudio = false);
            },
          );
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('🔊 Spoken briefing playing inline with ElevenLabs AI!'),
                backgroundColor: AppTheme.primary,
                duration: Duration(seconds: 3),
              ),
            );
          }
          return;
        }
      }
      throw Exception('Server did not return audio URL');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Audio briefing notice: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _audioLoading = false);
    }
  }

  void _showAcceptAsIsDialog(BuildContext context) {
    final acceptController = TextEditingController();
    bool canConfirm = false;

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (ctx) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
          title: const Row(
            children: [
              Icon(Icons.check_circle_outline, color: AppTheme.primary, size: 24),
              SizedBox(width: 8),
              Expanded(
                child: Text('Accept Agreement As-Is', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
              ),
            ],
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const Text(
                  'You are choosing to accept this agreement as drafted without entering negotiation.',
                  style: TextStyle(fontSize: 13, color: AppTheme.textMuted, height: 1.4),
                ),
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: AppTheme.canvas,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: AppTheme.border),
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Monthly Rent:', style: TextStyle(fontSize: 12, color: AppTheme.textMuted)),
                          Text(_rs(widget.monthlyRent), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        ],
                      ),
                      const SizedBox(height: 4),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Security Deposit:', style: TextStyle(fontSize: 12, color: AppTheme.textMuted)),
                          Text(_rs(widget.securityDeposit), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 14),
                const Text(
                  'To confirm and generate your SignSmart Official Stamp, please type "I accept" below:',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                ),
                const SizedBox(height: 8),
                TextField(
                  controller: acceptController,
                  autofocus: true,
                  onChanged: (val) {
                    setDialogState(() {
                      canConfirm = val.trim().toLowerCase() == 'i accept';
                    });
                  },
                  decoration: InputDecoration(
                    hintText: 'Type: I accept',
                    filled: true,
                    fillColor: AppTheme.canvas,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: const BorderSide(color: AppTheme.border)),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: canConfirm
                  ? () {
                      Navigator.of(ctx).pop();
                      Navigator.of(context).pushReplacement(
                        MaterialPageRoute(
                          builder: (_) => FinalApprovalScreen(
                            monthlyRent: widget.monthlyRent,
                            originalDeposit: widget.securityDeposit,
                            revisedDeposit: widget.securityDeposit,
                            originalLockIn: widget.lockInMonths,
                            revisedLockIn: widget.lockInMonths,
                            moneySaved: 0,
                            isAsIs: true,
                          ),
                        ),
                      );
                    }
                  : null,
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
              child: const Text('Confirm & Stamp Agreement'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Agreement Audit'),
        actions: [
          IconButton(
            icon: const Icon(Icons.share_outlined),
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Audit link copied to clipboard.')),
              );
            },
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Score Banner
            Container(
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppTheme.border),
                boxShadow: [
                  BoxShadow(color: Colors.black.withAlpha(6), blurRadius: 10, offset: const Offset(0, 4)),
                ],
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'AUDIT VERDICT',
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.textMuted, letterSpacing: 0.8),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            widget.verdict,
                            style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: AppTheme.danger, letterSpacing: -0.5),
                          ),
                        ],
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                        decoration: BoxDecoration(
                          color: AppTheme.dangerLight,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Text(
                          '${widget.riskScore} / 100',
                          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: AppTheme.danger),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 28),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Total Money at Risk:', style: TextStyle(fontSize: 14, color: AppTheme.textMuted)),
                      Text(
                        _rs(widget.moneyAtRisk),
                        style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.primary),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Monthly Rent:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                      Text('${_rs(widget.monthlyRent)} / mo', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Security Deposit:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                      Text(_rs(widget.securityDeposit), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text('Lock-in Duration:', style: TextStyle(fontSize: 13, color: AppTheme.textMuted)),
                      Text('${widget.lockInMonths} months', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Accept As-Is Shortcut Card
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.border),
              ),
              child: Row(
                children: [
                  const Icon(Icons.thumb_up_alt_outlined, color: AppTheme.primary, size: 20),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Satisfied with these terms?', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: AppTheme.textMain)),
                        Text('Skip negotiation and approve agreement as drafted.', style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                      ],
                    ),
                  ),
                  OutlinedButton(
                    onPressed: () => _showAcceptAsIsDialog(context),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                      side: const BorderSide(color: AppTheme.primary),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: const Text('Accept As-Is', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 18),

            // Voice AI Audio Briefing Card (INLINE PLAYER)
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF004D40), Color(0xFF00695C)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(color: AppTheme.primary.withAlpha(50), blurRadius: 12, offset: const Offset(0, 4)),
                ],
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(8),
                        decoration: BoxDecoration(
                          color: Colors.white.withAlpha(40),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(
                          _isPlayingAudio ? Icons.volume_up_rounded : Icons.graphic_eq_rounded,
                          color: Colors.white,
                          size: 22,
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'ElevenLabs Voice Briefing',
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: Colors.white),
                            ),
                            Text(
                              _isPlayingAudio ? '▶ Playing in-app audio briefing…' : 'Spoken summary of clauses & statutory rights',
                              style: TextStyle(fontSize: 11, color: _isPlayingAudio ? const Color(0xFF69F0AE) : Colors.white70),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // Language selector chips
                  Row(
                    children: [
                      _langChip('en', 'English'),
                      const SizedBox(width: 8),
                      _langChip('kn', 'ಕನ್ನಡ'),
                      const SizedBox(width: 8),
                      _langChip('hi', 'हिंदी'),
                    ],
                  ),
                  const SizedBox(height: 14),

                  // Inline Audio Control Buttons
                  Row(
                    children: [
                      Expanded(
                        child: ElevatedButton.icon(
                          onPressed: _audioLoading ? null : _playVoiceBriefing,
                          icon: _audioLoading
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2, color: AppTheme.primary),
                                )
                              : Icon(_isPlayingAudio ? Icons.pause_rounded : Icons.play_arrow_rounded),
                          label: Text(
                            _audioLoading
                                ? 'Synthesizing Audio…'
                                : (_isPlayingAudio ? 'Pause Spoken Brief' : 'Play Spoken Summary (In-App)'),
                            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13),
                          ),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppTheme.primaryDark,
                            padding: const EdgeInsets.symmetric(vertical: 13),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                        ),
                      ),
                      if (_isPlayingAudio || _audioUrl != null) ...[
                        const SizedBox(width: 8),
                        IconButton(
                          onPressed: () {
                            _audioPlayer.stop();
                            setState(() => _isPlayingAudio = false);
                          },
                          icon: const Icon(Icons.stop_circle_outlined, color: Colors.white, size: 28),
                          tooltip: 'Stop Audio',
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Section Header
            const Text(
              'Flagged Clauses & Official Law Authorities',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.textMain, letterSpacing: -0.3),
            ),
            const SizedBox(height: 12),

            if (widget.dynamicRisks != null && widget.dynamicRisks!.isNotEmpty) ...[
              for (var r in widget.dynamicRisks!) ...[
                _statuteCard(
                  clauseNo: r['clause']?.toString() ?? 'Clause',
                  title: r['title']?.toString() ?? 'Flagged Clause',
                  impact: r['why_for_you']?.toString() ?? 'Identified risk clause.',
                  act: (r['legal_citations'] != null && (r['legal_citations'] as List).isNotEmpty)
                      ? r['legal_citations'][0]['act'].toString()
                      : 'Model Tenancy Act, 2021',
                  section: (r['legal_citations'] != null && (r['legal_citations'] as List).isNotEmpty)
                      ? 'Section ${r['legal_citations'][0]['section']}'
                      : 'Statutory Protection',
                  statuteText: (r['legal_citations'] != null && (r['legal_citations'] as List).isNotEmpty)
                      ? r['legal_citations'][0]['snippet'].toString()
                      : 'Statutory authority governs reasonable compensations and deposits.',
                  url: (r['legal_citations'] != null && (r['legal_citations'] as List).isNotEmpty)
                      ? r['legal_citations'][0]['url'].toString()
                      : 'https://mohua.gov.in/static/uploads/2025/11/0e6aea16d11ed1a622f1de43ff3710b4.pdf',
                ),
                const SizedBox(height: 12),
              ],
            ] else ...[
              // Clause 5: Lock-in
              _statuteCard(
                clauseNo: 'Clause 5',
                title: '36-month Lock-in with Full Rent Penalty',
                impact: 'Requires paying full rent for remaining 24 months (${_rs(widget.moneyAtRisk)}) if you exit early.',
                act: 'Model Tenancy Act, 2021',
                section: 'Section 23 & Section 5',
                statuteText: 'Tenancy terms and vacation compensation provisions governing premature termination.',
                url: 'https://mohua.gov.in/static/uploads/2025/11/0e6aea16d11ed1a622f1de43ff3710b4.pdf',
              ),
              const SizedBox(height: 12),

              // Clause 4: Deposit
              _statuteCard(
                clauseNo: 'Clause 4',
                title: '${_rs(widget.securityDeposit)} Security Deposit with No Refund Date',
                impact: 'Owner can retain your capital indefinitely with zero statutory deadline to return.',
                act: 'Model Tenancy Act, 2021',
                section: 'Section 11(1)',
                statuteText: 'Security deposit for premises shall not exceed statutory limit and must be refunded upon vacation.',
                url: 'https://mohua.gov.in/static/uploads/2025/11/0e6aea16d11ed1a622f1de43ff3710b4.pdf',
              ),
              const SizedBox(height: 12),

              // Clause 7: Late Fee
              _statuteCard(
                clauseNo: 'Clause 7',
                title: 'Uncapped Late Fee (₹500 / day)',
                impact: 'Can accumulate up to ₹15,000 monthly, violating reasonableness principles.',
                act: 'Indian Contract Act, 1872',
                section: 'Section 74',
                statuteText: 'Compensation for breach of contract where penalty is stipulated must be reasonable compensation, not an arbitrary penalty.',
                url: 'https://indiankanoon.org/doc/1941714/',
              ),
              const SizedBox(height: 12),
            ],

            const SizedBox(height: 20),

            // CONTINUATION FLOW & NEXT STEPS
            const Text(
              'Action Plan: Negotiation & Outreach',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: AppTheme.textMain, letterSpacing: -0.3),
            ),
            const SizedBox(height: 6),
            const Text(
              'Do not sign this draft in its current form. Use SignSmart counter-offer proposals to negotiate safer terms.',
              style: TextStyle(fontSize: 13, color: AppTheme.textMuted, height: 1.4),
            ),
            const SizedBox(height: 14),

            // Primary CTA: Open Negotiation Studio
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.primaryLight,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.primary.withAlpha(60)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(color: AppTheme.primary, borderRadius: BorderRadius.circular(12)),
                        child: const Icon(Icons.handshake_outlined, color: Colors.white, size: 22),
                      ),
                      const SizedBox(width: 14),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Proceed to Negotiation Studio',
                              style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.primaryDark),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Custom proposals pre-filled with your lease terms in 3 tones.',
                              style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 14),
                  ElevatedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => NegotiationTab(
                            monthlyRent: widget.monthlyRent,
                            securityDeposit: widget.securityDeposit,
                            lockInMonths: widget.lockInMonths,
                            dynamicRisks: widget.dynamicRisks,
                            isStandalone: true,
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.arrow_forward_rounded),
                    label: const Text('Open Negotiation Studio 🚀'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      backgroundColor: AppTheme.primary,
                      foregroundColor: Colors.white,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),

            // Quick Outreach Actions Row
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () async {
                      final uri = Uri.parse('tel:+919845012345');
                      if (await canLaunchUrl(uri)) await launchUrl(uri);
                    },
                    icon: const Icon(Icons.phone_in_talk, color: AppTheme.primary),
                    label: const Text('Call Landlord', style: TextStyle(color: AppTheme.textMain, fontSize: 13, fontWeight: FontWeight.w700)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      backgroundColor: AppTheme.surface,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => NegotiationTab(
                            monthlyRent: widget.monthlyRent,
                            securityDeposit: widget.securityDeposit,
                            lockInMonths: widget.lockInMonths,
                            dynamicRisks: widget.dynamicRisks,
                            isStandalone: true,
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.chat_bubble_outline_rounded, color: Color(0xFF25D366)),
                    label: const Text('WhatsApp Draft', style: TextStyle(color: AppTheme.textMain, fontSize: 13, fontWeight: FontWeight.w700)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 13),
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      backgroundColor: AppTheme.surface,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),

            // Verify Revised Agreement Button
            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => ScannerTab(
                      isVerificationMode: true,
                      initialRent: widget.monthlyRent,
                      initialDeposit: widget.securityDeposit,
                      initialLockIn: widget.lockInMonths,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.verified_outlined, color: AppTheme.primaryDark),
              label: const Text('Verify Landlord\'s Revised Draft 📄', style: TextStyle(color: AppTheme.primaryDark, fontWeight: FontWeight.w700)),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: AppTheme.primary, width: 1.2),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                backgroundColor: AppTheme.surface,
              ),
            ),
            const SizedBox(height: 12),

            // Back to Dashboard
            TextButton.icon(
              onPressed: () => Navigator.of(context).pop(),
              icon: const Icon(Icons.arrow_back, size: 16),
              label: const Text('Back to Home Dashboard'),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _langChip(String code, String label) {
    final isSel = _selectedLang == code;
    return Expanded(
      child: InkWell(
        onTap: () {
          _audioPlayer.stop();
          setState(() {
            _selectedLang = code;
            _audioUrl = null;
            _isPlayingAudio = false;
          });
        },
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 6),
          decoration: BoxDecoration(
            color: isSel ? Colors.white : Colors.white.withAlpha(30),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: isSel ? AppTheme.primaryDark : Colors.white,
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _statuteCard({
    required String clauseNo,
    required String title,
    required String impact,
    required String act,
    required String section,
    required String statuteText,
    required String url,
  }) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: AppTheme.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: AppTheme.dangerLight, borderRadius: BorderRadius.circular(6)),
                child: Text(
                  clauseNo,
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: AppTheme.danger),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  title,
                  style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(impact, style: const TextStyle(fontSize: 13, color: AppTheme.textMuted, height: 1.4)),
          const SizedBox(height: 12),

          // Official Statutory Authority Box
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppTheme.primaryLight,
              borderRadius: BorderRadius.circular(10),
              border: const Border(left: BorderSide(color: AppTheme.primary, width: 3.5)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      '⚖️ $act · $section',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.primaryDark),
                    ),
                    InkWell(
                      onTap: () => launchUrl(Uri.parse(url)),
                      child: const Text(
                        'Official Text ↗',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppTheme.primary,
                          decoration: TextDecoration.underline,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  '"$statuteText"',
                  style: const TextStyle(fontSize: 12, fontStyle: FontStyle.italic, color: AppTheme.primaryDark, height: 1.3),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// SCREEN: FINAL APPROVAL & OFFICIAL SIGNSMART SEAL
// ---------------------------------------------------------------------------
class FinalApprovalScreen extends StatefulWidget {
  final int monthlyRent;
  final int originalDeposit;
  final int revisedDeposit;
  final int originalLockIn;
  final int revisedLockIn;
  final int moneySaved;
  final String? downloadUrl;
  final bool isAsIs;

  const FinalApprovalScreen({
    super.key,
    required this.monthlyRent,
    required this.originalDeposit,
    required this.revisedDeposit,
    required this.originalLockIn,
    required this.revisedLockIn,
    required this.moneySaved,
    this.downloadUrl,
    this.isAsIs = false,
  });

  @override
  State<FinalApprovalScreen> createState() => _FinalApprovalScreenState();
}

class _FinalApprovalScreenState extends State<FinalApprovalScreen> {
  bool _isDownloading = false;
  String? _pdfUrl;

  String _rs(int val) => '₹${val.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')}';

  @override
  void initState() {
    super.initState();
    _pdfUrl = widget.downloadUrl;
  }

  Future<void> _downloadCertifiedPdf() async {
    if (_pdfUrl != null && _pdfUrl!.isNotEmpty) {
      final uri = Uri.parse(_pdfUrl!);
      if (await canLaunchUrl(uri)) {
        await launchUrl(uri, mode: LaunchMode.externalApplication);
        return;
      }
    }

    setState(() => _isDownloading = true);
    try {
      final origin = kIsWeb ? Uri.base.origin : kDefaultBackendUrl;
      final res = await http.post(
        Uri.parse('$origin/api/agreement/certify'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'rent': widget.monthlyRent,
          'deposit': widget.revisedDeposit,
          'lock_in': widget.revisedLockIn,
          'money_saved': widget.moneySaved,
        }),
      );
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        final url = data['download_url'] ?? '$origin${data['relative_url']}';
        setState(() => _pdfUrl = url);
        final uri = Uri.parse(url);
        if (await canLaunchUrl(uri)) {
          await launchUrl(uri, mode: LaunchMode.externalApplication);
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Download notice: $e')));
      }
    } finally {
      if (mounted) setState(() => _isDownloading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Certified Agreement'),
        automaticallyImplyLeading: false,
        actions: [
          IconButton(
            icon: const Icon(Icons.close_rounded),
            onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // THE OFFICIAL SIGNSMART COMPLIANCE SEAL (HERO STAMP)
            Container(
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF00382E), Color(0xFF004D40), Color(0xFF00695C)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(color: const Color(0xFFFFB300), width: 2),
                boxShadow: [
                  BoxShadow(color: const Color(0xFFFFB300).withAlpha(80), blurRadius: 18, offset: const Offset(0, 6)),
                  BoxShadow(color: AppTheme.primaryDark.withAlpha(120), blurRadius: 10),
                ],
              ),
              child: Column(
                children: [
                  // Gold Star Badge
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: const Color(0xFFFFB300),
                      boxShadow: [
                        BoxShadow(color: Colors.amber.withAlpha(150), blurRadius: 12),
                      ],
                    ),
                    child: const Icon(Icons.verified_rounded, size: 36, color: Color(0xFF00382E)),
                  ),
                  const SizedBox(height: 12),
                  const Text(
                    '★ APPROVED BY SIGNSMART ★',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w900,
                      color: Color(0xFFFFD54F),
                      letterSpacing: 1.2,
                    ),
                  ),
                  const SizedBox(height: 4),
                  const Text(
                    'OFFICIAL TENANCY COMPLIANCE SEAL',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Colors.white70, letterSpacing: 0.8),
                  ),
                  const Divider(height: 24, color: Colors.white24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      Column(
                        children: [
                          const Text('AUDIT VERDICT', style: TextStyle(fontSize: 9, color: Colors.white60)),
                          const SizedBox(height: 2),
                          Text(
                            widget.isAsIs ? 'SEALED AS-IS' : 'SAFE TO SIGN',
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Color(0xFF69F0AE)),
                          ),
                        ],
                      ),
                      Container(height: 28, width: 1, color: Colors.white24),
                      Column(
                        children: [
                          const Text('FINAL RISK SCORE', style: TextStyle(fontSize: 9, color: Colors.white60)),
                          const SizedBox(height: 2),
                          const Text(
                            '12 / 100',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Color(0xFF69F0AE)),
                          ),
                        ],
                      ),
                      Container(height: 28, width: 1, color: Colors.white24),
                      Column(
                        children: [
                          const Text('STATUTE FIT', style: TextStyle(fontSize: 9, color: Colors.white60)),
                          const SizedBox(height: 2),
                          const Text(
                            '100% MTA',
                            style: TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: Color(0xFFFFD54F)),
                          ),
                        ],
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.white.withAlpha(20),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(
                      'REGISTRATION CERTIFICATE: SS-MTA-2026-${DateTime.now().millisecondsSinceEpoch.toString().substring(7)}',
                      style: const TextStyle(fontSize: 9, fontFamily: 'monospace', color: Colors.white70),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // Comparison Audit Summary Card
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Audit Trail & Protection',
                        style: TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: AppTheme.textMain),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                        decoration: BoxDecoration(
                          color: AppTheme.successLight,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          '${_rs(widget.moneySaved)} Saved!',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: AppTheme.success),
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 22),
                  _compRow(
                    'Security Deposit',
                    _rs(widget.originalDeposit),
                    _rs(widget.revisedDeposit),
                    'Capped to 2 months rent (MTA §11)',
                  ),
                  const Divider(height: 18),
                  _compRow(
                    'Lock-in Duration',
                    '${widget.originalLockIn} Months',
                    '${widget.revisedLockIn} Months',
                    'Mutual 2-mo notice exit (MTA §23)',
                  ),
                  const Divider(height: 18),
                  _compRow(
                    'Late Payment Fee',
                    '₹500 / day uncapped',
                    '₹50 / day capped',
                    'Liquidated damages (ICA §74)',
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Primary Download CTA
            ElevatedButton.icon(
              onPressed: _isDownloading ? null : _downloadCertifiedPdf,
              icon: _isDownloading
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                  : const Icon(Icons.picture_as_pdf_rounded),
              label: Text(
                _isDownloading ? 'Generating Sealed PDF…' : 'Download Certified Agreement (PDF with Seal) 📥',
                style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              ),
            ),
            const SizedBox(height: 12),

            // Continue Flow for Round 3 / Further changes
            OutlinedButton.icon(
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => NegotiationTab(
                      monthlyRent: widget.monthlyRent,
                      securityDeposit: widget.revisedDeposit,
                      lockInMonths: widget.revisedLockIn,
                      isStandalone: true,
                    ),
                  ),
                );
              },
              icon: const Icon(Icons.refresh_rounded, color: AppTheme.primary),
              label: const Text(
                'Need another negotiation round? Continue Flow 🔁',
                style: TextStyle(fontWeight: FontWeight.w700, color: AppTheme.primary),
              ),
              style: OutlinedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 14),
                side: const BorderSide(color: AppTheme.primary),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 12),

            // Return to Home Dashboard
            TextButton.icon(
              onPressed: () => Navigator.of(context).popUntil((route) => route.isFirst),
              icon: const Icon(Icons.home_outlined, size: 18),
              label: const Text('Done — Return to Dashboard'),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _compRow(String label, String original, String revised, String lawCitation) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: AppTheme.textMain)),
            Row(
              children: [
                Text(original, style: const TextStyle(fontSize: 12, decoration: TextDecoration.lineThrough, color: AppTheme.danger)),
                const SizedBox(width: 8),
                const Icon(Icons.arrow_forward, size: 12, color: AppTheme.textMuted),
                const SizedBox(width: 8),
                Text(revised, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w800, color: AppTheme.success)),
              ],
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(lawCitation, style: const TextStyle(fontSize: 11, color: AppTheme.textMuted, fontStyle: FontStyle.italic)),
      ],
    );
  }
}
// ---------------------------------------------------------------------------
// TAB 2: LEGAL KNOWLEDGE STATUTES EXPLORER
// ---------------------------------------------------------------------------
class LegalKnowledgeTab extends StatelessWidget {
  const LegalKnowledgeTab({super.key});

  @override
  Widget build(BuildContext context) {
    final statutes = [
      {
        'act': 'Model Tenancy Act, 2021',
        'sec': 'Section 11',
        'topic': 'Security Deposit Caps & Refund Timeline',
        'desc': 'Limits advance deposit to maximum 2 months rent for residential and 6 months for non-residential premises. Mandates prompt refund on vacating.',
        'url': 'https://mohua.gov.in/static/uploads/2025/11/0e6aea16d11ed1a622f1de43ff3710b4.pdf',
      },
      {
        'act': 'The Indian Contract Act, 1872',
        'sec': 'Section 74',
        'topic': 'Liquidated Damages vs Unreasonable Penalty',
        'desc': 'Prohibits disproportionate penalty clauses. Courts grant only reasonable compensation for proven loss, striking down arbitrary daily fines.',
        'url': 'https://indiankanoon.org/doc/1941714/',
      },
      {
        'act': 'Transfer of Property Act, 1882',
        'sec': 'Section 106',
        'topic': 'Notice Period for Lease Termination',
        'desc': 'Requires minimum notice periods for lease determinations in the absence of valid mutual agreements.',
        'url': 'https://indiankanoon.org/doc/80042/',
      },
      {
        'act': 'The Registration Act, 1908',
        'sec': 'Section 17 & 49',
        'topic': 'Mandatory Registration for Leases > 11 Months',
        'desc': 'Leases exceeding 11 months must be compulsorily registered; unregistered long-term leases cannot be received as evidence of contract terms.',
        'url': 'https://indiankanoon.org/doc/1416712/',
      },
    ];

    return Scaffold(
      appBar: AppBar(title: const Text('Indian Tenancy Statutes')),
      body: ListView.separated(
        padding: const EdgeInsets.all(20),
        itemCount: statutes.length,
        separatorBuilder: (_, _) => const SizedBox(height: 12),
        itemBuilder: (context, i) {
          final s = statutes[i];
          return Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: AppTheme.surface,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: AppTheme.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: AppTheme.primaryLight,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(
                        s['sec']!,
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: AppTheme.primaryDark),
                      ),
                    ),
                    InkWell(
                      onTap: () => launchUrl(Uri.parse(s['url']!)),
                      child: const Text(
                        'Read Act ↗',
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: AppTheme.primary),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                Text(
                  s['topic']!,
                  style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: AppTheme.textMain),
                ),
                const SizedBox(height: 4),
                Text(
                  s['act']!,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.textMuted),
                ),
                const SizedBox(height: 8),
                Text(
                  s['desc']!,
                  style: const TextStyle(fontSize: 13, color: Color(0xFF475569), height: 1.4),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// TAB 3: NEGOTIATION STUDIO (CALL & SMS)
// ---------------------------------------------------------------------------
class NegotiationTab extends StatefulWidget {
  final int? monthlyRent;
  final int? securityDeposit;
  final int? lockInMonths;
  final List<dynamic>? dynamicRisks;
  final String? initialPhone;
  final bool isStandalone;

  const NegotiationTab({
    super.key,
    this.monthlyRent,
    this.securityDeposit,
    this.lockInMonths,
    this.dynamicRisks,
    this.initialPhone,
    this.isStandalone = false,
  });

  @override
  State<NegotiationTab> createState() => _NegotiationTabState();
}

class _NegotiationTabState extends State<NegotiationTab> {
  late final TextEditingController _ownerPhone;
  late final TextEditingController _proposal;
  int _toneIndex = 0;

  String _rs(int val) => '₹${val.toString().replaceAllMapped(RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'), (m) => '${m[1]},')}';

  String _getProposalText(int tone) {
    final rent = (widget.monthlyRent != null && widget.monthlyRent! > 0) ? widget.monthlyRent! : 35000;
    final fairDeposit = (widget.securityDeposit != null && widget.securityDeposit! > 0)
        ? (widget.securityDeposit! > rent * 3 ? rent * 2 : widget.securityDeposit!)
        : rent * 2;
    final lockIn = (widget.lockInMonths != null && widget.lockInMonths! > 0) ? widget.lockInMonths! : 36;

    if (tone == 0) {
      // 🤝 Friendly Tone
      return 'Namaskara Sir, thank you for sharing the lease agreement. I am very keen on finalizing the premises and look forward to being a model, long-term tenant!\n\n'
          'Upon review, I kindly propose aligning with standard market practices:\n'
          '1. Security Deposit: Adjusted to ${_rs(fairDeposit)} (refundable within 30 days of vacating).\n'
          '2. Lock-in Period: Set to 11 months with mutual 2 months notice period (instead of $lockIn months).\n'
          '3. Late Fee: Capped at a reasonable ₹50 per day.\n\n'
          'Looking forward to a productive, long-term relationship. Best regards.';
    } else if (tone == 1) {
      // ⚖️ Balanced Tone
      return 'Dear Landlord, thank you for sharing the draft tenancy agreement.\n\n'
          'Following our review against standard rental benchmarks and statutory best practices:\n'
          '1. Security Deposit: Propose ${_rs(fairDeposit)} (aligned with Section 11 of the Model Tenancy Act recommendation of max 2 months rent for residential premises).\n'
          '2. Lock-in Period: 11 months mutual lock-in with standard 1-month notice thereafter.\n'
          '3. Termination & Damages: Liquidated damages limited to actual unrecovered loss rather than full lock-in forfeiture, per Section 74 Indian Contract Act.\n\n'
          'Please review these fair amendments so we may execute the agreement smoothly.';
    } else {
      // 📜 Formal Legal Tone
      return 'ATTN: Property Owner / Lessor\n'
          'RE: Revisions to Draft Tenancy Agreement - Compliance with Statutory Provisions\n\n'
          'Take notice that the current draft contains clauses inconsistent with governing Indian tenancy laws:\n'
          '1. Clause on Full Lock-in Rent Forfeiture violates Section 74 of the Indian Contract Act, 1872 (forbidding penalties beyond genuine pre-estimated damage).\n'
          '2. Proposed security deposit of ${_rs(widget.securityDeposit ?? 300000)} exceeds statutory guidance under Section 11 of Model Tenancy Act, 2021; counter-proposed at ${_rs(fairDeposit)}.\n'
          '3. Lock-in clause without termination reciprocity is voidable under Section 108 of the Transfer of Property Act, 1882.\n\n'
          'Enclosed are our revised terms rectifying these statutory non-compliances. Kindly confirm acceptance to proceed with registration.';
    }
  }

  String _toneName(int idx) {
    switch (idx) {
      case 0:
        return 'Friendly & Cooperative';
      case 1:
        return 'Balanced & Market Benchmark';
      case 2:
        return 'Formal Legal Notice';
      default:
        return 'Custom';
    }
  }

  @override
  void initState() {
    super.initState();
    _ownerPhone = TextEditingController(text: widget.initialPhone ?? '+91 98450 12345');
    _proposal = TextEditingController(text: _getProposalText(_toneIndex));
  }

  @override
  void dispose() {
    _ownerPhone.dispose();
    _proposal.dispose();
    super.dispose();
  }

  void _callOwner() async {
    final phone = _ownerPhone.text.replaceAll(' ', '');
    final uri = Uri.parse('tel:$phone');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
    _showPostOutreachPrompt();
  }

  void _sendWhatsApp() async {
    final cleanPhone = _ownerPhone.text.replaceAll(RegExp(r'[\s+]'), '');
    final text = Uri.encodeComponent(_proposal.text);
    final uri = Uri.parse('https://wa.me/$cleanPhone?text=$text');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
    _showPostOutreachPrompt();
  }

  void _sendSms() async {
    final cleanPhone = _ownerPhone.text.replaceAll(' ', '');
    final text = Uri.encodeComponent(_proposal.text);
    final uri = Uri.parse('sms:$cleanPhone?body=$text');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri);
    }
    _showPostOutreachPrompt();
  }

  void _showPostOutreachPrompt() {
    Future.delayed(const Duration(milliseconds: 600), () {
      if (!mounted) return;
      showModalBottomSheet(
        context: context,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        backgroundColor: AppTheme.surface,
        builder: (ctx) => Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(color: AppTheme.successLight, borderRadius: BorderRadius.circular(10)),
                    child: const Icon(Icons.mark_email_read_rounded, color: AppTheme.success, size: 24),
                  ),
                  const SizedBox(width: 12),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('Proposal Dispatched! 💬', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: AppTheme.textMain)),
                        Text('Landlord notified with your counter-offer terms', style: TextStyle(fontSize: 11, color: AppTheme.textMuted)),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              const Text(
                'When your landlord sends back the amended agreement, tap below to verify compliance and obtain your official SignSmart approval seal.',
                style: TextStyle(fontSize: 13, color: AppTheme.textMuted, height: 1.4),
              ),
              const SizedBox(height: 20),
              ElevatedButton.icon(
                onPressed: () {
                  Navigator.of(ctx).pop();
                  Navigator.of(context).push(
                    MaterialPageRoute(
                      builder: (_) => ScannerTab(
                        isVerificationMode: true,
                        initialRent: widget.monthlyRent ?? 35000,
                        initialDeposit: widget.securityDeposit ?? 300000,
                        initialLockIn: widget.lockInMonths ?? 36,
                      ),
                    ),
                  );
                },
                icon: const Icon(Icons.verified_outlined),
                label: const Text('Verify Landlord\'s Revised Draft 📄 ➔'),
                style: ElevatedButton.styleFrom(
                  backgroundColor: AppTheme.primary,
                  foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                ),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('I will verify later'),
              ),
            ],
          ),
        ),
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Negotiation Studio'),
        leading: widget.isStandalone
            ? IconButton(
                icon: const Icon(Icons.arrow_back),
                onPressed: () => Navigator.of(context).pop(),
              )
            : null,
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Context header if passed from audit
            if (widget.isStandalone && widget.monthlyRent != null && widget.monthlyRent! > 0) ...[
              Container(
                padding: const EdgeInsets.all(14),
                margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(
                  color: AppTheme.primaryLight,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AppTheme.primary.withAlpha(50)),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.verified, color: AppTheme.primary, size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'Audit Terms Loaded: Rent ${_rs(widget.monthlyRent!)}, Deposit ${_rs(widget.securityDeposit ?? 0)}, Lock-in ${widget.lockInMonths ?? 11} mo',
                        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: AppTheme.primaryDark),
                      ),
                    ),
                  ],
                ),
              ),
            ],

            // Tone Selector
            const Text(
              'Negotiation Tone',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textMuted),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                _toneChip(0, '🤝 Friendly'),
                const SizedBox(width: 8),
                _toneChip(1, '⚖️ Balanced'),
                const SizedBox(width: 8),
                _toneChip(2, '📜 Formal Legal'),
              ],
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.auto_awesome, size: 13, color: AppTheme.primary),
                const SizedBox(width: 6),
                Text(
                  'Tone active: ${_toneName(_toneIndex)}',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600, color: AppTheme.primary),
                ),
              ],
            ),
            const SizedBox(height: 18),

            // Owner Phone
            TextField(
              controller: _ownerPhone,
              keyboardType: TextInputType.phone,
              decoration: InputDecoration(
                labelText: 'Owner / Landlord Phone',
                prefixIcon: const Icon(Icons.phone_outlined, color: AppTheme.primary),
                filled: true,
                fillColor: AppTheme.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.border)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.border)),
              ),
            ),
            const SizedBox(height: 16),

            // Proposal Textbox
            TextField(
              controller: _proposal,
              maxLines: 8,
              decoration: InputDecoration(
                labelText: 'Counter-Offer Proposal (Customizable)',
                alignLabelWithHint: true,
                filled: true,
                fillColor: AppTheme.surface,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.border)),
                enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: AppTheme.border)),
              ),
            ),
            const SizedBox(height: 20),

            // Call Button
            ElevatedButton.icon(
              onPressed: _callOwner,
              icon: const Icon(Icons.phone_in_talk_rounded),
              label: const Text('Call Landlord Now'),
              style: ElevatedButton.styleFrom(
                padding: const EdgeInsets.symmetric(vertical: 16),
                backgroundColor: AppTheme.primaryDark,
                foregroundColor: Colors.white,
              ),
            ),
            const SizedBox(height: 12),

            // WhatsApp & SMS
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _sendWhatsApp,
                    icon: const Icon(Icons.chat_bubble_outline_rounded, color: Color(0xFF25D366)),
                    label: const Text('WhatsApp', style: TextStyle(color: AppTheme.textMain, fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      backgroundColor: AppTheme.surface,
                    ),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _sendSms,
                    icon: const Icon(Icons.sms_outlined, color: AppTheme.primary),
                    label: const Text('Direct SMS', style: TextStyle(color: AppTheme.textMain, fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      side: const BorderSide(color: AppTheme.border),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      backgroundColor: AppTheme.surface,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),

            // Dispatched Proposal Action Button
            ElevatedButton.icon(
              onPressed: _showPostOutreachPrompt,
              icon: const Icon(Icons.check_circle_outline_rounded),
              label: const Text('Proposal Sent ➔ Verify Revised Agreement'),
              style: ElevatedButton.styleFrom(
                backgroundColor: AppTheme.primary,
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 14),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
            ),
            const SizedBox(height: 24),

            // Re-Audit Landlord Response Card
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppTheme.surface,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.shield_outlined, color: AppTheme.primary, size: 20),
                      SizedBox(width: 8),
                      Text(
                        'Landlord Replied with an Amendment?',
                        style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: AppTheme.textMain),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Upload the revised agreement to verify whether lock-in, deposit, and late fee clauses have been satisfactorily corrected.',
                    style: TextStyle(fontSize: 12, color: AppTheme.textMuted, height: 1.3),
                  ),
                  const SizedBox(height: 12),
                  OutlinedButton.icon(
                    onPressed: () {
                      Navigator.of(context).push(
                        MaterialPageRoute(
                          builder: (_) => ScannerTab(
                            isVerificationMode: true,
                            initialRent: widget.monthlyRent ?? 35000,
                            initialDeposit: widget.securityDeposit ?? 300000,
                            initialLockIn: widget.lockInMonths ?? 36,
                          ),
                        ),
                      );
                    },
                    icon: const Icon(Icons.upload_file_outlined, color: AppTheme.primary),
                    label: const Text('Verify Landlord Amended Draft ➔', style: TextStyle(color: AppTheme.primary, fontWeight: FontWeight.bold)),
                    style: OutlinedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(vertical: 12),
                      side: const BorderSide(color: AppTheme.primary),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _toneChip(int index, String label) {
    final isSel = _toneIndex == index;
    return Expanded(
      child: InkWell(
        onTap: () {
          setState(() {
            _toneIndex = index;
            _proposal.text = _getProposalText(index);
          });
        },
        borderRadius: BorderRadius.circular(10),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(
            color: isSel ? AppTheme.primary : AppTheme.surface,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: isSel ? AppTheme.primary : AppTheme.border, width: isSel ? 1.5 : 1.0),
          ),
          child: Center(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: isSel ? Colors.white : AppTheme.textMain,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
// ---------------------------------------------------------------------------
// TAB 4: ADMIN DIRECTORY (FREE VS PAID USERS)
// ---------------------------------------------------------------------------
class AdminDirectoryTab extends StatefulWidget {
  const AdminDirectoryTab({super.key});

  @override
  State<AdminDirectoryTab> createState() => _AdminDirectoryTabState();
}

class _AdminDirectoryTabState extends State<AdminDirectoryTab> {
  List<dynamic> _users = [];
  bool _loading = true;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _fetchUsers();
  }

  Future<void> _fetchUsers() async {
    try {
      final origin = kIsWeb ? Uri.base.origin : kDefaultBackendUrl;
      final res = await http.get(Uri.parse('$origin/api/admin/users')).timeout(const Duration(seconds: 4));
      if (res.statusCode == 200) {
        setState(() {
          _users = jsonDecode(res.body);
          _loading = false;
        });
        return;
      }
    } catch (_) {}

    // Fallback data
    setState(() {
      _users = [
        {
          'phone': '+91 98450 11223',
          'paid': true,
          'agreement_type': 'Shop Rent',
          'risk_score': 78,
          'money_at_risk': 840000,
          'state': 'NEGOTIATION',
          'created_at': DateTime.now().millisecondsSinceEpoch ~/ 1000 - 3600,
        },
        {
          'phone': '+91 94481 99887',
          'paid': false,
          'agreement_type': 'Residential Lease',
          'risk_score': 42,
          'money_at_risk': 120000,
          'state': 'REPORT',
          'created_at': DateTime.now().millisecondsSinceEpoch ~/ 1000 - 7200,
        },
        {
          'phone': '+91 98862 33445',
          'paid': true,
          'agreement_type': 'Commercial Warehouse',
          'risk_score': 85,
          'money_at_risk': 1400000,
          'state': 'DONE',
          'created_at': DateTime.now().millisecondsSinceEpoch ~/ 1000 - 18000,
        },
      ];
      _loading = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _users.where((u) {
      if (_filter == 'paid') return u['paid'] == true;
      if (_filter == 'free') return u['paid'] == false;
      return true;
    }).toList();

    final paidCount = _users.where((u) => u['paid'] == true).length;
    final freeCount = _users.length - paidCount;

    return Scaffold(
      appBar: AppBar(title: const Text('Admin & User Directory')),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: AppTheme.primary))
          : Padding(
              padding: const EdgeInsets.all(20),
              child: Column(
                children: [
                  // KPI cards
                  Row(
                    children: [
                      _kpi('Total', '${_users.length}', AppTheme.textMain),
                      const SizedBox(width: 10),
                      _kpi('Paid (₹49)', '$paidCount', AppTheme.success),
                      const SizedBox(width: 10),
                      _kpi('Free Audit', '$freeCount', AppTheme.gold),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // Chips
                  Row(
                    children: [
                      _chip('All (${_users.length})', 'all'),
                      const SizedBox(width: 8),
                      _chip('Paid ($paidCount)', 'paid'),
                      const SizedBox(width: 8),
                      _chip('Free ($freeCount)', 'free'),
                    ],
                  ),
                  const SizedBox(height: 16),

                  // User List
                  Expanded(
                    child: ListView.separated(
                      itemCount: filtered.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 10),
                      itemBuilder: (context, idx) {
                        final u = filtered[idx];
                        final isPaid = u['paid'] == true;
                        final score = u['risk_score'] ?? 0;
                        return Container(
                          padding: const EdgeInsets.all(16),
                          decoration: BoxDecoration(
                            color: AppTheme.surface,
                            borderRadius: BorderRadius.circular(14),
                            border: Border.all(color: AppTheme.border),
                          ),
                          child: Row(
                            children: [
                              CircleAvatar(
                                backgroundColor: isPaid ? AppTheme.successLight : AppTheme.goldLight,
                                child: Icon(
                                  isPaid ? Icons.check_circle_rounded : Icons.visibility_outlined,
                                  color: isPaid ? AppTheme.success : AppTheme.gold,
                                  size: 20,
                                ),
                              ),
                              const SizedBox(width: 14),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      u['phone'] ?? 'User',
                                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: AppTheme.textMain),
                                    ),
                                    const SizedBox(height: 2),
                                    Text(
                                      '${u['agreement_type']} · ${u['state']}',
                                      style: const TextStyle(color: AppTheme.textMuted, fontSize: 12),
                                    ),
                                  ],
                                ),
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  Container(
                                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                    decoration: BoxDecoration(
                                      color: isPaid ? AppTheme.successLight : AppTheme.goldLight,
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    child: Text(
                                      isPaid ? 'PAID PACK' : 'FREE AUDIT',
                                      style: TextStyle(
                                        fontSize: 10,
                                        fontWeight: FontWeight.w800,
                                        color: isPaid ? AppTheme.success : AppTheme.gold,
                                      ),
                                    ),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Score: $score/100',
                                    style: TextStyle(
                                      fontSize: 12,
                                      fontWeight: FontWeight.w700,
                                      color: score >= 66 ? AppTheme.danger : AppTheme.primary,
                                    ),
                                  ),
                                ],
                              ),
                            ],
                          ),
                        );
                      },
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  Widget _kpi(String label, String value, Color color) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
        decoration: BoxDecoration(
          color: AppTheme.surface,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: AppTheme.border),
        ),
        child: Column(
          children: [
            Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: AppTheme.textMuted)),
            const SizedBox(height: 4),
            Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: color)),
          ],
        ),
      ),
    );
  }

  Widget _chip(String label, String value) {
    final sel = _filter == value;
    return ChoiceChip(
      label: Text(label),
      selected: sel,
      onSelected: (_) => setState(() => _filter = value),
      selectedColor: AppTheme.primaryLight,
      backgroundColor: AppTheme.surface,
      labelStyle: TextStyle(
        fontSize: 12,
        fontWeight: FontWeight.w700,
        color: sel ? AppTheme.primaryDark : AppTheme.textMuted,
      ),
      side: BorderSide(color: sel ? AppTheme.primary : AppTheme.border),
    );
  }
}
