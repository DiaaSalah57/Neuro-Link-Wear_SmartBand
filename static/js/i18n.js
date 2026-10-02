import { translateKnownClinicalText } from './ai-locales.js?v=20261002-1';

/**
 * Front-end English / Arabic localization for NeuroLink Wear.
 *
 * The UI uses a local phrasebook so names, clinical notes and health readings
 * are never sent to a third-party translation service. Unknown/user-entered
 * text is intentionally left untouched.
 */
const ARABIC = {
  /* Login and product introduction */
  'NeuroLink Wear — Health & Safety Dashboard': 'NeuroLink Wear — لوحة الصحة والسلامة',
  'Health & safety monitoring': 'مراقبة الصحة والسلامة',
  'that never sleeps.': 'على مدار الساعة.',
  'Real-time biometrics, AI-driven anomaly detection and one-press emergency escalation — built for elderly individuals, their families and caregivers.': 'مؤشرات حيوية مباشرة، واكتشاف ذكي للحالات غير الطبيعية، وطلب مساعدة طارئ بلمسة واحدة — صُممت لكبار السن وعائلاتهم ومقدمي الرعاية.',
  'Live vitals': 'المؤشرات الحيوية المباشرة',
  'HR · SpO₂ · temperature · GSR stress': 'النبض · الأكسجين · الحرارة · مؤشر التوتر',
  'AI insights': 'رؤى الذكاء الاصطناعي',
  'Plain-language explanations & advice': 'تفسيرات ونصائح واضحة',
  'Instant escalation': 'طلب مساعدة فوري',
  'GPS tracking & one-click dispatch': 'تتبع GPS وإرسال طلب المساعدة بلمسة واحدة',
  'Welcome back': 'مرحبًا بعودتك',
  'Sign in to the NeuroLink Wear dashboard': 'سجّل الدخول إلى لوحة NeuroLink Wear',
  'Email': 'البريد الإلكتروني',
  'Password': 'كلمة المرور',
  'Sign in': 'تسجيل الدخول',
  'Signing in…': 'جارٍ تسجيل الدخول…',
  'Quick sign-in accounts — one click to fill': 'حسابات تسجيل دخول سريعة — اضغط مرة لملء البيانات',
  'Malak (Caregiver)': 'ملاك (مقدمة رعاية)',
  'Diaa (Admin)': 'ضياء (مسؤول)',

  /* App shell, navigation and header */
  'Live Overview': 'نظرة عامة مباشرة',
  'AI Alerts': 'تنبيهات الذكاء الاصطناعي',
  'Safety & SOS': 'السلامة والاستغاثة',
  'Trends': 'الاتجاهات',
  'Care Team': 'فريق الرعاية',
  'System': 'النظام',
  'Settings': 'الإعدادات',
  'Connecting…': 'جارٍ الاتصال…',
  'Reconnecting…': 'جارٍ إعادة الاتصال…',
  'Device Online': 'الجهاز متصل',
  'Device Offline': 'الجهاز غير متصل',
  'NeuroLink Band': 'سوار NeuroLink',
  'last sync —': 'آخر مزامنة —',
  'Toggle dark / light mode': 'التبديل بين الوضع الداكن والفاتح',
  'Toggle theme': 'تغيير المظهر',
  'Trigger emergency SOS': 'إرسال نداء استغاثة طارئ',
  'Open menu': 'فتح القائمة',
  'Close menu': 'إغلاق القائمة',
  'Sign out': 'تسجيل الخروج',
  'Administrator': 'مسؤول النظام',
  'Caregiver': 'مقدم الرعاية',
  'User': 'مستخدم',

  /* Overview */
  'Heart Rate': 'معدل ضربات القلب',
  'Blood Oxygen': 'الأكسجين في الدم',
  'Skin Temperature': 'درجة حرارة الجلد',
  'Stress Index (GSR)': 'مؤشر التوتر (GSR)',
  'live': 'مباشر',
  '→ steady': '→ مستقر',
  'Safe': 'آمن',
  'Motion state from IMU classifier': 'حالة الحركة حسب مستشعر الحركة IMU',
  'Live Overview': 'نظرة عامة مباشرة',
  'Real-time biometrics streaming from the NeuroLink Wear band — updated every 2 seconds.': 'مؤشرات حيوية مباشرة من سوار NeuroLink Wear — يتم التحديث كل ثانيتين.',
  'Refresh': 'تحديث',
  'Generate AI summary': 'إنشاء ملخص ذكي',
  'Motion & IMU Status': 'الحركة وحالة مستشعر IMU',
  'accelerometer + gyroscope': 'مقياس التسارع + الجيروسكوب',
  'Accelerometer': 'مقياس التسارع',
  'Gyroscope': 'الجيروسكوب',
  'Steps today': 'الخطوات اليوم',
  'Fall-detection threshold: impact ≥ 2.8 g with rotation ≥ 2.4 rad/s — the band auto-escalates on match.': 'حد اكتشاف السقوط: صدمة ≥ 2.8 g مع دوران ≥ 2.4 rad/s — يرسل السوار تنبيهًا تلقائيًا عند تحقق ذلك.',
  'Live Event Feed': 'سجل الأحداث المباشرة',
  'streaming': 'جارٍ البث',
  'Wearable Device': 'الجهاز القابل للارتداء',
  'NeuroLink AI Insight': 'رؤى NeuroLink AI',
  'Quick Actions': 'إجراءات سريعة',
  'Trigger emergency SOS': 'إرسال نداء استغاثة طارئ',
  'Fall Detected · "Are you OK?" (30s)': 'تم اكتشاف سقوط · «هل أنت بخير؟» (30 ثانية)',
  'Dispatch emergency contacts': 'إخطار جهات الاتصال للطوارئ',
  'Open safety & live map': 'فتح السلامة والخريطة المباشرة',
  'Demo scenario controls': 'التحكم في سيناريو العرض',
  'Simulate fall': 'محاكاة سقوط',
  'Stress spike': 'ارتفاع التوتر',
  'Fever': 'حمّى',
  'Low SpO₂': 'انخفاض الأكسجين',
  'Battery': 'البطارية',
  'Last sync': 'آخر مزامنة',
  'Online': 'متصل',
  'Offline': 'غير متصل',
  'No device paired': 'لا يوجد جهاز مقترن',
  'Pair a NeuroLink band in Care Team → Devices.': 'اقرن سوار NeuroLink من فريق الرعاية ← الأجهزة.',
  'wellbeing score': 'مؤشر العافية',
  'just now · wellbeing score': 'الآن · مؤشر العافية',
  'Daily health summary — yesterday': 'ملخص الصحة اليومي — أمس',
  'Daily health summary — 2 days ago': 'ملخص الصحة اليومي — منذ يومين',
  'Daily health summary — 5 days ago': 'ملخص الصحة اليومي — منذ 5 أيام',
  'incomplete-data': 'بيانات غير مكتملة',
  'good-mobility': 'حركة جيدة',
  'family-notified': 'تم إخطار العائلة',
  'recovered': 'متعافٍ',
  'sleep-improving': 'تحسن النوم',
  'hydration': 'الترطيب',
  'improving-baseline': 'تحسن خط الأساس',
  'fall-prevention': 'الوقاية من السقوط',
  'sleep-watch': 'مراقبة النوم',
  'Read full analysis': 'قراءة التحليل الكامل',
  'No AI summaries yet': 'لا توجد ملخصات ذكية بعد',
  'Generate one from the button above.': 'أنشئ ملخصًا باستخدام الزر أعلاه.',
  'Telemetry refreshed': 'تم تحديث بيانات القياس',
  'Waiting for wearable data': 'بانتظار بيانات السوار',
  'No readings received from the band yet.': 'لم تصل أي قراءات من السوار بعد.',
  'AI summary generated': 'تم إنشاء الملخص الذكي',
  'Fresh analysis added to the insights feed.': 'أُضيف تحليل جديد إلى سجل الرؤى.',
  'Could not generate summary': 'تعذر إنشاء الملخص',
  'Scenario triggered': 'تم تشغيل السيناريو',
  'Trigger failed': 'تعذر تشغيل السيناريو',
  'Simulate fall': 'محاكاة سقوط',
  'Stress': 'التوتر',
  'Impact': 'الصدمة',
  'Temp': 'الحرارة',
  'ML Score': 'نتيجة نموذج التعلم الآلي',
  'HR': 'النبض',
  'SpO₂': 'الأكسجين SpO₂',
  'HRV': 'تباين نبض القلب HRV',
  'GSR': 'استجابة الجلد GSR',
  'Sleeping': 'نائم',
  'Resting': 'مستريح',
  'Walking': 'يمشي',
  'Running': 'يركض',
  'Exercising': 'يمارس الرياضة',

  /* Alerts and AI insights */
  'AI Insights & Alerts': 'رؤى وتنبيهات الذكاء الاصطناعي',
  'Every anomaly is detected in real time and explained in plain language by NeuroLink AI, with concrete next steps for the care team.': 'يكتشف NeuroLink AI كل حالة غير طبيعية مباشرة ويشرحها بوضوح، مع خطوات عملية لفريق الرعاية.',
  'New AI summary': 'ملخص ذكي جديد',
  'Incident alerts': 'تنبيهات الحوادث',
  'AI health summaries': 'ملخصات الصحة الذكية',
  'All': 'الكل',
  'Active': 'نشط',
  'Acknowledged': 'تم الإقرار',
  'Resolved': 'تم الحل',
  'Critical': 'حرج',
  'High': 'مرتفع',
  'Medium': 'متوسط',
  'Low': 'منخفض',
  'No alerts match these filters': 'لا توجد تنبيهات تطابق عوامل التصفية',
  'Try widening the date range or clearing the status / severity filters.': 'جرّب توسيع النطاق الزمني أو إزالة عوامل تصفية الحالة والخطورة.',
  'Clear filters': 'مسح عوامل التصفية',
  'No incidents recorded': 'لا توجد حوادث مسجلة',
  'NeuroLink AI is watching every reading. The moment a stress spike, fever, low-oxygen episode or fall is detected, it will appear here with a full explanation.': 'يراقب NeuroLink AI كل قراءة. سيظهر هنا فور اكتشاف ارتفاع في التوتر أو حمّى أو انخفاض في الأكسجين أو سقوط، مع شرح كامل.',
  'How NeuroLink AI works': 'كيف يعمل NeuroLink AI',
  '1 · Detect.': '1 · الاكتشاف.',
  'An ensemble of threshold rules, an Isolation Forest and an LSTM autoencoder watch every reading for anomalies in stress, temperature, oxygen and motion.': 'تراقب مجموعة من قواعد الحدود ونموذج Isolation Forest ومشفّر LSTM كل قراءة لاكتشاف التغيّرات في التوتر والحرارة والأكسجين والحركة.',
  '2 · Explain.': '2 · التفسير.',
  'Each detection is turned into a plain-language explanation referencing the exact sensor values — no jargon.': 'يُحوّل كل اكتشاف إلى شرح واضح يشير إلى قيم المستشعرات الفعلية — دون مصطلحات معقدة.',
  '3 · Advise.': '3 · التوصية.',
  'Actionable recommendations are attached to every incident, and daily summaries track the bigger picture.': 'تُرفق بكل حادث توصيات عملية، وتعرض الملخصات اليومية الصورة العامة.',
  'Summaries refresh on demand and after major incidents.': 'تُحدّث الملخصات عند الطلب وبعد الحوادث المهمة.',
  'Tier 3 ML model explanation': 'شرح نموذج التعلم الآلي — المستوى الثالث',
  'AI explanation': 'شرح الذكاء الاصطناعي',
  'Recommended actions': 'الإجراءات الموصى بها',
  'ML Model · AI-flagged': 'نموذج تعلم آلي · رصد بالذكاء الاصطناعي',
  'Ensemble Evidence': 'أدلة النماذج المجمعة',
  'Peak σ-evidence': 'أعلى دليل σ',
  'z(GSR phasic)': 'z (استجابة GSR المرحلية)',
  'z(HRV drop)': 'z (انخفاض HRV)',
  'Core-equiv temp': 'درجة الحرارة المكافئة للنواة',
  'Hypoxic burden': 'عبء نقص الأكسجين',
  'Isolation Forest score': 'نتيجة Isolation Forest',
  'Are you OK? (30s check)': 'هل أنت بخير؟ (تحقق خلال 30 ثانية)',
  'Acknowledge': 'إقرار',
  'Mark resolved': 'تحديد كمحلول',
  'Dispatch contacts': 'إخطار جهات الاتصال',
  'View on map': 'عرض على الخريطة',
  'resolved by': 'تم الحل بواسطة',
  'No AI summaries yet': 'لا توجد ملخصات ذكية بعد',
  'Click “New AI summary” to compose one from the last 24 hours of readings.': 'اضغط «ملخص ذكي جديد» لإنشاء ملخص من قراءات آخر 24 ساعة.',
  'Could not load summaries': 'تعذر تحميل الملخصات',
  'Alert acknowledged': 'تم الإقرار بالتنبيه',
  'Your name is now attached to the incident timeline.': 'أُضيف اسمك إلى سجل الحادث.',
  'Resolve this alert?': 'هل تريد حل هذا التنبيه؟',
  'This marks the incident as handled and moves it out of the active queue.': 'سيُسجّل الحادث على أنه تمت معالجته ويُزال من قائمة التنبيهات النشطة.',
  'Mark resolved': 'تحديد كمحلول',
  'Alert resolved': 'تم حل التنبيه',
  'Moved to the resolved incidents log.': 'نُقل إلى سجل الحوادث المحلولة.',
  'Action failed': 'تعذر تنفيذ الإجراء',
  'AI summary ready': 'الملخص الذكي جاهز',
  'A fresh analysis was added to the summaries tab.': 'أُضيف تحليل جديد إلى تبويب الملخصات.',
  'Generation failed': 'فشل الإنشاء',

  /* Alert labels / known condition and status values */
  'Fall Detected': 'تم اكتشاف سقوط',
  'Low Oxygen': 'انخفاض الأكسجين',
  'High Stress': 'ارتفاع التوتر',
  'Panic Attack': 'نوبة هلع',
  'Tachycardia': 'تسارع ضربات القلب',
  'Bradycardia': 'بطء ضربات القلب',
  'Fatigue': 'إرهاق',
  'Inactivity': 'عدم حركة',
  'General Anomaly': 'حالة غير طبيعية عامة',
  'Emergency SOS': 'نداء استغاثة طارئ',
  'critical': 'حرج',
  'high': 'مرتفع',
  'medium': 'متوسط',
  'low': 'منخفض',
  'active': 'نشط',
  'acknowledged': 'تم الإقرار',
  'resolved': 'تم الحل',
  'daily': 'يومي',
  'weekly': 'أسبوعي',
  'event': 'حدث',
  'fall': 'سقوط',
  'stress': 'توتر',
  'fever': 'حمّى',
  'desaturation': 'انخفاض الأكسجين',
  'stable-oxygen': 'أكسجين مستقر',
  'temperature-watch': 'مراقبة الحرارة',
  'stable-temperature': 'حرارة مستقرة',
  'stress-episode': 'نوبة توتر',
  'calm': 'هدوء',
  'fall-risk': 'خطر السقوط',

  /* Safety and emergency */
  'Safety & Emergency': 'السلامة والطوارئ',
  'Live GPS tracking, incident escalation and one-press dispatch to the people who can help fastest.': 'تتبع GPS مباشر، وتصعيد الحوادث، وإخطار الأشخاص القادرين على تقديم المساعدة بسرعة بلمسة واحدة.',
  'Emergency SOS': 'استغاثة طارئة',
  'Wearer status:': 'حالة مرتدي السوار:',
  'Safe': 'آمن',
  'Band is streaming · fall detection armed · GPS updating every 20 s': 'السوار يبث البيانات · اكتشاف السقوط مفعّل · تحديث GPS كل 20 ثانية',
  'Live Location': 'الموقع المباشر',
  'loading…': 'جارٍ التحميل…',
  'Live position': 'الموقع المباشر',
  'Incident location': 'موقع الحادث',
  'Today': 'اليوم',
  '7 days': '7 أيام',
  '30 days': '30 يومًا',
  'Incident Timeline': 'سجل الحوادث',
  'Escalation Status': 'حالة التصعيد',
  'Fall detection': 'اكتشاف السقوط',
  'Armed': 'مفعّل',
  'Inactivity monitor': 'مراقبة عدم الحركة',
  'Armed · 90 min': 'مفعّل · 90 دقيقة',
  'SOS button': 'زر الاستغاثة',
  'Ready': 'جاهز',
  'Emergency contacts': 'جهات اتصال الطوارئ',
  'Fall Check-In ("Are you OK?" 30s)': 'التحقق بعد السقوط («هل أنت بخير؟» 30 ثانية)',
  'One-click dispatch': 'إرسال بلمسة واحدة',
  'Manage contacts': 'إدارة جهات الاتصال',
  'Inactivity Monitor': 'مراقبة عدم الحركة',
  'Recent Dispatches': 'عمليات الإخطار الأخيرة',
  'No incidents recorded today': 'لا توجد حوادث مسجلة اليوم',
  'No incidents in this period': 'لا توجد حوادث خلال هذه الفترة',
  'A quiet day is a good day. Falls, low-oxygen events and distress episodes will appear here the instant they happen.': 'اليوم الهادئ يوم جيد. ستظهر هنا فورًا حالات السقوط أو انخفاض الأكسجين أو الضيق عند حدوثها.',
  'Nothing to show for this date range — widen it to see older events.': 'لا توجد بيانات ضمن هذا النطاق الزمني — وسّع النطاق لعرض أحداث أقدم.',
  'Map': 'الخريطة',
  'Resolve': 'حلّ',
  'Dispatch now': 'إخطار الآن',
  'Resolve this incident?': 'هل تريد حل هذا الحادث؟',
  'It will be moved to the resolved log.': 'سيُنقل إلى سجل الحوادث المحلولة.',
  'Acknowledged': 'تم الإقرار',
  'Incident timeline updated.': 'تم تحديث سجل الحادث.',
  'Failed': 'فشل',
  'Incident resolved': 'تم حل الحادث',
  'No dispatches yet': 'لا توجد عمليات إخطار بعد',
  'Emergency contact dispatches will be logged here with delivery status.': 'ستُسجّل هنا إخطارات جهات الاتصال للطوارئ مع حالة التسليم.',
  'Dispatch emergency contacts': 'إخطار جهات الاتصال للطوارئ',
  'Incident:': 'الحادث:',
  'Choose who should be contacted. Each dispatch is logged in the incident timeline.': 'اختر جهات الاتصال المطلوبة. يُسجّل كل إخطار في سجل الحادث.',
  'primary': 'أساسي',
  'backup': 'احتياطي',
  'priority': 'الأولوية',
  'Message template': 'نص الرسالة',
  'Channel:': 'القناة:',
  'Phone call': 'مكالمة هاتفية',
  'App push': 'إشعار التطبيق',
  'Cancel': 'إلغاء',
  'Select at least one contact': 'اختر جهة اتصال واحدة على الأقل',
  'Choose who should be dispatched.': 'اختر الجهات التي تريد إخطارها.',
  'Delivery confirmed — logged in the incident record.': 'تم تأكيد التسليم — وسُجّل في ملف الحادث.',
  'Dispatch failed': 'فشل الإخطار',
  'Could not load contacts': 'تعذر تحميل جهات الاتصال',
  'Current state': 'الحالة الحالية',
  'Last movement': 'آخر حركة',
  'monitoring…': 'جارٍ الرصد…',
  'If no movement is detected for': 'إذا لم تُكتشف أي حركة لمدة',

  /* Trends and analytics */
  'Historical Trends & Analytics': 'الاتجاهات والتحليلات السابقة',
  'Interactive time-series for HRV, body temperature, stress variation and daily activity — with clinical thresholds overlaid.': 'مخططات زمنية لتباين نبض القلب وحرارة الجسم والتوتر والنشاط اليومي — مع إظهار الحدود الطبية.',
  '24 h': '24 ساعة',
  '48 h': '48 ساعة',
  '7 days': '7 أيام',
  '30 days': '30 يومًا',
  'Avg heart rate (24h)': 'متوسط نبض القلب (24 ساعة)',
  'Avg HRV (24h)': 'متوسط HRV (24 ساعة)',
  'Avg temperature': 'متوسط الحرارة',
  'Peak stress index': 'أعلى مؤشر للتوتر',
  'vs prev. 24h': 'مقارنة بـ 24 ساعة سابقة',
  'No readings in this range': 'لا توجد قراءات ضمن هذا النطاق',
  'Try a wider date range — the band stores 30 days of history.': 'جرّب نطاقًا زمنيًا أوسع — يحتفظ السوار بسجل 30 يومًا.',
  'Heart-Rate Variability': 'تباين معدل ضربات القلب',
  'autonomic recovery marker': 'مؤشر التعافي العصبي اللاإرادي',
  'Temperature & SpO₂': 'الحرارة والأكسجين SpO₂',
  'fever / desaturation watch': 'مراقبة الحمّى وانخفاض الأكسجين',
  'Stress Index vs Heart Rate': 'مؤشر التوتر مقارنة بنبض القلب',
  'GSR + HRV composite stress score': 'مؤشر توتر مركب من GSR وHRV',
  'Daily Activity Summary — 14 days': 'ملخص النشاط اليومي — 14 يومًا',
  'steps & active minutes': 'الخطوات والدقائق النشطة',
  "Today's motion mix": 'مزيج الحركة اليوم',
  'Active alerts': 'التنبيهات النشطة',
  'Min SpO₂ (24h)': 'أدنى SpO₂ (24 ساعة)',
  'Max temperature': 'أعلى درجة حرارة',
  'No statistics yet': 'لا توجد إحصاءات بعد',
  'Stats appear after the first readings stream in.': 'ستظهر الإحصاءات بعد وصول القراءات الأولى.',
  'No activity history': 'لا يوجد سجل للنشاط',
  'Daily summaries appear after the band has streamed for a day.': 'تظهر الملخصات اليومية بعد بث البيانات من السوار لمدة يوم.',
  'Activity breakdown appears once live readings accumulate.': 'سيظهر توزيع النشاط بعد تجميع القراءات المباشرة.',
  'Steps': 'الخطوات',
  'Active minutes': 'الدقائق النشطة',
  'Sleeping': 'نائم',
  'Resting': 'مستريح',
  'Walking': 'يمشي',
  'Running': 'يركض',
  'Exercising': 'يمارس الرياضة',
  'fatigue': 'إرهاق',
  'fever': 'حمّى',
  'high stress': 'توتر مرتفع',

  /* Care team, devices, contacts, profiles and thresholds */
  'Caregiver & Device Management': 'إدارة مقدمي الرعاية والأجهزة',
  'Emergency contacts, wearable device pairing, personalized alert thresholds and the care team.': 'جهات اتصال الطوارئ، وإقران الأجهزة القابلة للارتداء، وحدود التنبيه المخصصة، وفريق الرعاية.',
  'Emergency contacts': 'جهات اتصال الطوارئ',
  'Devices': 'الأجهزة',
  'Alert thresholds': 'حدود التنبيه',
  'Wearer profile': 'ملف مرتدي السوار',
  'Calibration': 'المعايرة',
  'Contacts': 'جهات الاتصال',
  'Team': 'الفريق',
  'Add emergency contact': 'إضافة جهة اتصال للطوارئ',
  'Edit contact': 'تعديل جهة الاتصال',
  'Full name': 'الاسم الكامل',
  'Relationship': 'صلة القرابة',
  'Phone': 'الهاتف',
  'Priority (1 = first)': 'الأولوية (1 = الأول)',
  'Can receive dispatch': 'يمكنه استقبال الإخطارات',
  'Yes': 'نعم',
  'No (informational only)': 'لا (للعلم فقط)',
  'Notes': 'ملاحظات',
  'Daughter, physician…': 'ابنة، طبيب…',
  'optional': 'اختياري',
  'Lives nearby, prefers SMS…': 'يسكن بالقرب، ويفضل الرسائل النصية…',
  'Save changes': 'حفظ التغييرات',
  'Add contact': 'إضافة جهة اتصال',
  'Name and phone are required': 'الاسم ورقم الهاتف مطلوبان',
  'Contact updated': 'تم تحديث جهة الاتصال',
  'Contact added': 'تمت إضافة جهة الاتصال',
  'is on the dispatch list.': 'أُضيف إلى قائمة الإخطار.',
  'Save failed': 'فشل الحفظ',
  'Could not load contacts': 'تعذر تحميل جهات الاتصال',
  'No emergency contacts saved': 'لا توجد جهات اتصال للطوارئ محفوظة',
  'Add at least one contact so emergency dispatch has somewhere to go.': 'أضف جهة اتصال واحدة على الأقل لتلقي الإخطارات في حالات الطوارئ.',
  'Add first contact': 'إضافة أول جهة اتصال',
  'saved · priority order controls the dispatch sequence': 'محفوظة · يحدد ترتيب الأولوية تسلسل الإخطار',
  'Priority': 'الأولوية',
  'Name': 'الاسم',
  'Dispatch': 'إخطار',
  'Actions': 'الإجراءات',
  'enabled': 'مفعّل',
  'off': 'متوقف',
  'Edit': 'تعديل',
  'Delete': 'حذف',
  'Delete contact?': 'هل تريد حذف جهة الاتصال؟',
  'will be removed from the emergency dispatch list.': 'ستُزال من قائمة الإخطار في حالات الطوارئ.',
  'Contact deleted': 'تم حذف جهة الاتصال',
  'removed from the dispatch list.': 'أُزيل من قائمة الإخطار.',
  'Delete failed — change rolled back': 'فشل الحذف — تم التراجع عن التغيير',
  'Edit wearable device': 'تعديل الجهاز القابل للارتداء',
  'Pair a new wearable': 'إقران جهاز جديد',
  'Device name': 'اسم الجهاز',
  'Model': 'الطراز',
  'Serial number': 'الرقم التسلسلي',
  'Firmware': 'البرنامج الثابت',
  'Test connection': 'اختبار الاتصال',
  'Testing…': 'جارٍ الاختبار…',
  'Device reachable': 'الجهاز متاح',
  'Connection verified.': 'تم التحقق من الاتصال.',
  'Connection test failed': 'فشل اختبار الاتصال',
  'Could not reach the wearable stream.': 'تعذر الاتصال ببث بيانات الجهاز القابل للارتداء.',
  'Save device': 'حفظ الجهاز',
  'Pair device': 'إقران الجهاز',
  'Name and serial are required': 'الاسم والرقم التسلسلي مطلوبان',
  'Device saved': 'تم حفظ الجهاز',
  'Device paired': 'تم إقران الجهاز',
  'is linked to Abdelrahman’s profile.': 'تم ربطه بملف Abdelrahman.',
  'Manage paired NeuroLink Wear bands and live device status.': 'إدارة أساور NeuroLink Wear المقترنة وحالة الأجهزة المباشرة.',
  'Pair device': 'إقران الجهاز',
  'read-only · admin manages devices': 'للقراءة فقط · يدير المسؤول الأجهزة',
  'online': 'متصل',
  'paired': 'مقترن',
  'charging': 'قيد الشحن',
  'Last seen': 'آخر ظهور',
  'Test': 'اختبار',
  'Edit device': 'تعديل الجهاز',
  'Remove': 'إزالة',
  'Device reachable': 'الجهاز متاح',
  'Connection verified.': 'تم التحقق من الاتصال.',
  'Test failed': 'فشل الاختبار',
  'Remove device?': 'هل تريد إزالة الجهاز؟',
  'will be unpaired and removed from this profile.': 'سيتم إلغاء إقرانه وإزالته من هذا الملف.',
  'Device removed': 'تمت إزالة الجهاز',
  'Remove failed': 'فشلت الإزالة',
  'Thresholds unavailable': 'الحدود غير متاحة',
  'Could not load alert thresholds.': 'تعذر تحميل حدود التنبيه.',
  'Personalized Health Alert Thresholds': 'حدود التنبيه الصحي المخصصة',
  'Reset to recommended': 'إعادة الضبط إلى القيم الموصى بها',
  'Alerts fire the moment a live reading crosses these limits. Values are tailored to Abdelrahman’s clinical profile (hypertension, mild COPD). Changes take effect on the next reading — typically within 2 seconds.': 'يصدر التنبيه عند تجاوز قراءة مباشرة لهذه الحدود. القيم مخصصة للملف الطبي لمرتدي السوار. تُطبّق التغييرات مع القراءة التالية — عادة خلال ثانيتين.',
  'Heart rate — safe window': 'معدل ضربات القلب — النطاق الآمن',
  'tachycardia / bradycardia alerts': 'تنبيهات تسارع أو بطء ضربات القلب',
  'Blood oxygen (SpO₂) minimum': 'الحد الأدنى لأكسجين الدم (SpO₂)',
  'low-oxygen alerts': 'تنبيهات انخفاض الأكسجين',
  'critical if −3%': 'حرج عند انخفاض 3٪',
  'Temperature — fever ceiling': 'درجة الحرارة — حد الحمّى',
  'fever alerts': 'تنبيهات الحمّى',
  'Temperature — low floor': 'درجة الحرارة — الحد الأدنى',
  'hypothermia watch': 'مراقبة انخفاض حرارة الجسم',
  'low': 'منخفض',
  'Stress index ceiling': 'الحد الأعلى لمؤشر التوتر',
  'from GSR + HRV composite score': 'من النتيجة المركبة لـ GSR وHRV',
  'stress': 'التوتر',
  'HRV fatigue floor': 'الحد الأدنى لـ HRV عند الإرهاق',
  'fatigue / overtraining alerts': 'تنبيهات الإرهاق أو الإجهاد الزائد',
  'Fall detection impact': 'قوة الصدمة لاكتشاف السقوط',
  'accelerometer threshold': 'حد مقياس التسارع',
  'Enable fall detection': 'تفعيل اكتشاف السقوط',
  'Inactivity alert': 'تنبيه عدم الحركة',
  'no movement during waking hours': 'عدم الحركة خلال ساعات الاستيقاظ',
  'monitor': 'مراقبة',
  'Save thresholds': 'حفظ الحدود',
  'Reset to recommended values': 'تمت إعادة الضبط إلى القيم الموصى بها',
  'Press Save to apply.': 'اضغط «حفظ» لتطبيق التغييرات.',
  'Thresholds saved': 'تم حفظ الحدود',
  'The detection engine is already using the new limits.': 'يستخدم محرك الاكتشاف الحدود الجديدة الآن.',
  'Add team member': 'إضافة عضو إلى الفريق',
  'Edit team member': 'تعديل عضو الفريق',
  'Role': 'الدور',
  'Admin': 'مسؤول',
  'New password (leave blank to keep)': 'كلمة مرور جديدة (اتركها فارغة للإبقاء على الحالية)',
  'Password (min 6 chars)': 'كلمة المرور (6 أحرف على الأقل)',
  'Create user': 'إنشاء مستخدم',
  'User updated': 'تم تحديث المستخدم',
  'User created': 'تم إنشاء المستخدم',
  'Admins only': 'للمسؤولين فقط',
  'Team management is restricted to administrator accounts.': 'إدارة الفريق متاحة لحسابات المسؤولين فقط.',
  'Role-based access: admins manage the platform, caregivers manage the care workflow.': 'صلاحيات حسب الدور: يدير المسؤولون المنصة، ويدير مقدمو الرعاية إجراءات الرعاية.',
  'Delete user?': 'هل تريد حذف المستخدم؟',
  'will lose dashboard access immediately.': 'سيفقد الوصول إلى لوحة التحكم فورًا.',
  'User deleted': 'تم حذف المستخدم',
  'Delete refused': 'تم رفض الحذف',
  'Wearer Profile': 'ملف مرتدي السوار',
  'read-only · admin edits profile': 'للقراءة فقط · يعدل المسؤول الملف',
  'Age': 'العمر',
  'Address': 'العنوان',
  'Medical conditions': 'الحالات الطبية',
  'Medications': 'الأدوية',
  'Emergency note': 'ملاحظة الطوارئ',
  'Save profile': 'حفظ الملف',
  'Profile updated': 'تم تحديث الملف',
  'Profile unavailable': 'الملف غير متاح',
  'Calibration unavailable': 'المعايرة غير متاحة',
  'Calibration — personalised baselines': 'المعايرة — خطوط أساس مخصصة',
  'Calibrated': 'تمت المعايرة',
  'Warming up': 'جارٍ التهيئة',
  'confidence': 'ثقة',
  'samples': 'عينات',
  'Auto-fit from 24 h data': 'ضبط تلقائي من بيانات 24 ساعة',
  'Personal baselines learn from the wearable stream automatically; guided reference measurements (oral thermometer, clinical pulse-oximeter, resting HR/HRV) add ground-truth offsets.': 'تتعلم خطوط الأساس الشخصية تلقائيًا من بيانات السوار؛ وتضيف القياسات المرجعية الموجهة (مقياس حرارة فموي، ومقياس أكسجين سريري، وHR/HRV أثناء الراحة) تصحيحات دقيقة.',
  'Clinical safety floors never move.': 'حدود السلامة الطبية ثابتة دائمًا.',
  'Personal baselines': 'خطوط الأساس الشخصية',
  'Resting HR': 'نبض القلب أثناء الراحة',
  'Resting HRV': 'HRV أثناء الراحة',
  'GSR tonic level': 'مستوى GSR المستمر',
  'GSR noise (MAD)': 'ضوضاء GSR (MAD)',
  'Skin temp (rest)': 'حرارة الجلد (أثناء الراحة)',
  'Skin→core offset': 'فرق حرارة الجلد والنواة',
  'SpO₂ band offset': 'فرق SpO₂ في السوار',
  'Resting SpO₂': 'SpO₂ أثناء الراحة',
  'Manual values stop auto-updating until you change them.': 'تتوقف القيم اليدوية عن التحديث التلقائي حتى تغيّرها.',
  'Save manual overrides': 'حفظ التعديلات اليدوية',
  'Guided reference measurements': 'قياسات مرجعية موجهة',
  'Measurement': 'القياس',
  'Clinical reading': 'القراءة السريرية',
  'Band reading at same moment (optional)': 'قراءة السوار في الوقت نفسه (اختياري)',
  'Note (optional)': 'ملاحظة (اختياري)',
  'Morning reading': 'قراءة الصباح',
  'Oral temp + band skin temp calibrates the personal skin→core offset.': 'تُعاير حرارة الفم وحرارة الجلد من السوار فرق الجلد والنواة الشخصي.',
  'Apply reference point': 'تطبيق نقطة مرجعية',
  'Reference history': 'سجل القياسات المرجعية',
  'When': 'الوقت',
  'Value': 'القيمة',
  'Band': 'السوار',
  'Applied as': 'طُبّق كـ',
  'Auto-fit complete': 'اكتمل الضبط التلقائي',
  'Baselines already stable': 'خطوط الأساس مستقرة بالفعل',
  'Auto-fit failed': 'فشل الضبط التلقائي',
  'Baselines saved': 'تم حفظ خطوط الأساس',
  'Missing value': 'قيمة مفقودة',
  'Enter the measurement reading': 'أدخل قراءة القياس',
  'Reference applied': 'تم تطبيق القياس المرجعي',
  'Reference failed': 'فشل القياس المرجعي',

  /* Settings */
  'Appearance and account preferences.': 'تفضيلات المظهر والحساب.',
  'Appearance': 'المظهر',
  'Dark mode': 'الوضع الداكن',
  'Switch between the light clinical theme and the dark night theme.': 'التبديل بين المظهر الطبي الفاتح والمظهر الليلي الداكن.',
  'Density': 'كثافة العرض',
  'Comfortable spacing for medical review sessions.': 'مسافات مريحة لمراجعة المعلومات الطبية.',
  'comfortable': 'مريح',
  'Account': 'الحساب',
  'Session': 'الجلسة',
  'persisted · expires in 30 days': 'محفوظة · تنتهي خلال 30 يومًا',
  'Permissions': 'الصلاحيات',
  'Full platform + team management': 'كامل المنصة وإدارة الفريق',
  'Care workflow + dispatch': 'إجراءات الرعاية والإخطار',
  'Sign out of this device': 'تسجيل الخروج من هذا الجهاز',

  /* Shared feedback, empty/loading states and common labels */
  'Nothing here yet': 'لا يوجد شيء هنا بعد',
  'Something went wrong': 'حدث خطأ ما',
  'Unknown error': 'خطأ غير معروف',
  'Back to overview': 'العودة إلى النظرة العامة',
  'Could not start fall check-in': 'تعذر بدء التحقق بعد السقوط',
  'FALL DETECTED': 'تم اكتشاف سقوط',
  'Are you OK?': 'هل أنت بخير؟',
  'press button = I’m OK · no answer in 30 s → help is called': 'اضغط «أنا بخير» · إذا لم يصل رد خلال 30 ثانية فسيتم طلب المساعدة',
  '✓ I’m OK (Cancel Alert)': '✓ أنا بخير (إلغاء التنبيه)',
  'Call Help Now': 'اطلب المساعدة الآن',
  'Confirmed: I’m OK': 'تم التأكيد: أنا بخير',
  'Fall alert marked as false alarm — emergency escalation cancelled.': 'تم اعتبار تنبيه السقوط إنذارًا كاذبًا — أُلغي طلب المساعدة الطارئ.',
  'CRITICAL EMERGENCY — Help Called': 'حالة طارئة حرجة — تم طلب المساعدة',
  'Fall check update failed': 'فشل تحديث التحقق من السقوط',
  'Trigger emergency SOS?': 'هل تريد إرسال نداء استغاثة طارئ؟',
  'This raises a critical incident immediately, shares the live GPS position and opens the dispatch panel for the emergency contact list.': 'سيؤدي ذلك إلى تسجيل حالة حرجة فورًا ومشاركة موقع GPS المباشر وفتح لوحة إخطار جهات اتصال الطوارئ.',
  'Yes — send SOS': 'نعم — أرسل الاستغاثة',
  'SOS triggered': 'تم إرسال الاستغاثة',
  'Emergency incident created — dispatching contacts is the next step.': 'تم تسجيل حالة طارئة — الخطوة التالية هي إخطار جهات الاتصال.',
  'SOS failed': 'فشل إرسال الاستغاثة',
  'Could not start the session': 'تعذر بدء الجلسة',
  'Please try signing in again.': 'يرجى محاولة تسجيل الدخول مجددًا.',
  'Secure session started — it will persist for 30 days.': 'بدأت جلسة آمنة — وستظل محفوظة لمدة 30 يومًا.',
  'Unexpected server response — please retry': 'استجابة غير متوقعة من الخادم — يرجى المحاولة مجددًا',
  'Cannot reach the dashboard server — it may be restarting. Please wait a moment and try again.': 'تعذر الاتصال بخادم لوحة التحكم — قد يكون قيد إعادة التشغيل. انتظر قليلًا ثم حاول مجددًا.',
  'Sign-in failed': 'فشل تسجيل الدخول',
  'Nothing to show': 'لا توجد بيانات للعرض',
  'Select': 'اختيار',
  'SMS': 'رسالة نصية',
  'App push': 'إشعار التطبيق',
  'Just now': 'الآن',
  'Band battery': 'بطارية السوار',
  'Contact': 'جهة اتصال',
  'Prior': 'سابق',
  'Literature prior': 'مرجع علمي مسبق',
  'Auto-calibrated': 'معايرة تلقائية',
  'Guided reference': 'مرجع موجّه',
  'Manual': 'يدوي',
  'HRV (ms)': 'تباين نبض القلب HRV (ms)',
  'Skin temperature (°C)': 'حرارة الجلد (°C)',
  'SpO₂ (%)': 'الأكسجين SpO₂ (%)',
  'Stress index': 'مؤشر التوتر',
  'Heart rate (bpm ÷ 120)': 'معدل ضربات القلب (bpm ÷ 120)',
  'Active emergency:': 'حالة طوارئ نشطة:',
  'Overnight desaturation': 'انخفاض الأكسجين ليلًا',
  'Fall incident analysis': 'تحليل حادث السقوط',
  'Scenario': 'السيناريو',
  'Close': 'إغلاق',
  'Satellite': 'قمر صناعي',
  'No data in this range': 'لا توجد بيانات ضمن هذا النطاق',
  'Primary emergency contacts': 'جهات اتصال الطوارئ الأساسية',
  'Map tiles could not be loaded (offline?).': 'تعذر تحميل خرائط الموقع (هل الاتصال غير متاح؟)',
  'GPS coordinates are shown above and stay accurate.': 'تظهر إحداثيات GPS أعلاه وتبقى دقيقة.',
  'Map tiles unavailable — GPS coordinates remain live and accurate': 'خرائط الموقع غير متاحة — تظل إحداثيات GPS مباشرة ودقيقة',
  'If no movement is detected for': 'إذا لم تُكتشف أي حركة لمدة',
  'during waking hours, an inactivity alert is raised and the': 'خلال ساعات الاستيقاظ، يصدر تنبيه لعدم الحركة ويتم إخطار',
  'care team is notified — silent falls and unattended rest periods are caught automatically.': 'فريق الرعاية — ويتم رصد السقوط الصامت وفترات الراحة الطويلة تلقائيًا.',
  'Oral thermometer reading (calibrates skin→core offset)': 'قراءة مقياس الحرارة الفموي (لمعايرة الفرق بين حرارة الجلد والنواة)',
  'Clinical pulse-oximeter SpO2 (calibrates band SpO2 offset)': 'مقياس تأكسج سريري SpO₂ (لمعايرة فرق الأكسجين في السوار)',
  'Measured resting heart rate (bpm)': 'معدل ضربات القلب المقاس أثناء الراحة (bpm)',
  'Measured resting HRV (ms)': 'قيمة HRV المقاسة أثناء الراحة (ms)',
};

const normalize = (value) => String(value ?? '').replace(/\u00a0/g, ' ').trim().replace(/\s+/g, ' ');
const dictionary = new Map(Object.entries(ARABIC).map(([english, arabic]) => [normalize(english).toLocaleLowerCase('en'), arabic]));
const textState = new WeakMap();
const attributeState = new WeakMap();
let language = 'en';
let largeText = false;
let observer = null;

function localizedRelative(source) {
  const value = normalize(source).toLowerCase();
  if (value === 'just now') return 'الآن';
  const match = value.match(/^(\d+)\s*([smhd])\s+ago$/);
  if (!match) return null;
  const units = { s: 'ث', m: 'د', h: 'س', d: 'ي' };
  return `منذ ${match[1]} ${units[match[2]]}`;
}

/** Translate only a known interface phrase or a safe, name-preserving pattern. */
export function translateText(source) {
  const normalized = normalize(source);
  if (!normalized) return source;
  const exact = dictionary.get(normalized.toLocaleLowerCase('en'));
  if (exact) return exact;

  const clinical = translateKnownClinicalText(normalized);
  if (clinical) return clinical;

  const relative = localizedRelative(normalized);
  if (relative) return relative;

  let match = normalized.match(/^welcome,\s*(.+)$/i);
  if (match) return `مرحبًا، ${match[1]}`;
  match = normalized.match(/^(\d+)% confidence · (\d+) samples$/i);
  if (match) return `${match[1]}٪ ثقة · ${match[2]} عينة`;
  match = normalized.match(/^Daily health summary — yesterday$/i);
  if (match) return 'ملخص الصحة اليومي — أمس';
  match = normalized.match(/^Daily health summary — (.+)$/i);
  if (match) return `ملخص الصحة اليومي — ${match[1]}`;
  match = normalized.match(/^(.+) detected$/i);
  if (match) {
    const condition = dictionary.get(normalize(match[1]).toLocaleLowerCase('en'));
    if (condition) return `${condition} — تنبيه جديد`;
  }
  match = normalized.match(/^(.+) is on the dispatch list\.$/i);
  if (match) return `${match[1]} أُضيف إلى قائمة الإخطار.`;
  match = normalized.match(/^(.+) is linked to (.+)'s profile\.$/i);
  if (match) return `${match[1]} مرتبط بملف ${match[2]}.`;
  match = normalized.match(/^(.+) removed from the dispatch list\.$/i);
  if (match) return `${match[1]} أُزيل من قائمة الإخطار.`;
  match = normalized.match(/^last sync\s+(.+)$/i);
  if (match) return `آخر مزامنة ${localizedRelative(match[1]) || match[1]}`;
  match = normalized.match(/^safe\s+(.+)$/i);
  if (match) return `النطاق الآمن ${match[1]}`;
  match = normalized.match(/^Alerts fire the moment a live reading crosses these limits\. Values are tailored to (.+?)'s clinical profile \(hypertension, mild COPD\)\. Changes take effect on the next reading — typically within 2 seconds\.$/i);
  if (match) return `يصدر التنبيه فور تجاوز القراءة المباشرة لهذه الحدود. القيم مخصصة للملف الطبي لـ ${match[1]} (ارتفاع ضغط الدم وانسداد رئوي مزمن خفيف). تُطبّق التغييرات مع القراءة التالية — عادة خلال ثانيتين.`;
  match = normalized.match(/^(\d+) saved · priority order controls the dispatch sequence$/i);
  if (match) return `${match[1]} جهة محفوظة · يحدد ترتيب الأولوية تسلسل الإخطار`;
  match = normalized.match(/^(\d+) active alerts? need(s)? attention$/i);
  if (match) return `${match[1]} تنبيهات نشطة تحتاج إلى الانتباه`;
  match = normalized.match(/^auto-dispatched to (.+)\.$/i);
  if (match) {
    const destination = dictionary.get(normalize(match[1]).toLocaleLowerCase('en')) || match[1];
    return `تم الإخطار تلقائيًا إلى ${destination}.`;
  }
  match = normalized.match(/^dispatched to (\d+) contacts?$/i);
  if (match) return `تم إخطار ${match[1]} جهة اتصال`;
  match = normalized.match(/^resolved by (.+?) · (.+)$/i);
  if (match) return `تم الحل بواسطة ${match[1]} · ${localizedRelative(match[2]) || match[2]}`;
  match = normalized.match(/^by (.+)$/i);
  if (match) return `بواسطة ${match[1]}`;
  match = normalized.match(/^(\d+) saved$/i);
  if (match) return `${match[1]} جهة اتصال محفوظة`;
  match = normalized.match(/^(\d+) contacts?$/i);
  if (match) return `${match[1]} جهة اتصال`;
  match = normalized.match(/^(\d+) fall event\(s\) were recorded today\.$/i);
  if (match) return `${match[1]} حالة سقوط سُجّلت اليوم.`;
  match = normalized.match(/^(\d+) readings?$/i);
  if (match) return `${match[1]} قراءة`;
  match = normalized.match(/^(\d+) samples?$/i);
  if (match) return `${match[1]} عينة`;
  return source;
}

function isExcluded(element) {
  return Boolean(element?.closest?.('[data-i18n-ignore], [translate="no"], .notranslate'));
}

function spaced(source, replacement) {
  const leading = source.match(/^\s*/)?.[0] || '';
  const trailing = source.match(/\s*$/)?.[0] || '';
  return `${leading}${replacement}${trailing}`;
}

function localizeTextNode(node) {
  if (!node || !node.parentElement || isExcluded(node.parentElement)) return;
  // Never rewrite form values, editable notes, or user-authored content.
  if (node.parentElement.closest('textarea, [contenteditable="true"]')) return;
  const current = node.nodeValue;
  let state = textState.get(node);
  if (!state) {
    state = { source: current, rendered: current };
    textState.set(node, state);
  } else if (current !== state.rendered) {
    // The application changed the value of a text node after it was localized.
    state.source = current;
  }
  const next = language === 'ar' ? spaced(state.source, translateText(state.source)) : state.source;
  state.rendered = next;
  if (current !== next) node.nodeValue = next;
}

const TRANSLATABLE_ATTRIBUTES = ['title', 'aria-label', 'placeholder', 'alt'];
function localizeAttributes(element) {
  if (!element || element.nodeType !== 1 || isExcluded(element)) return;
  let states = attributeState.get(element);
  if (!states) {
    states = new Map();
    attributeState.set(element, states);
  }
  TRANSLATABLE_ATTRIBUTES.forEach((attribute) => {
    if (!element.hasAttribute(attribute)) return;
    const current = element.getAttribute(attribute);
    let state = states.get(attribute);
    if (!state) {
      state = { source: current, rendered: current };
      states.set(attribute, state);
    } else if (current !== state.rendered) {
      state.source = current;
    }
    const next = language === 'ar' ? translateText(state.source) : state.source;
    state.rendered = next;
    if (current !== next) element.setAttribute(attribute, next);
  });
}

function localizeSubtree(root) {
  if (!root) return;
  if (root.nodeType === 3) {
    localizeTextNode(root);
    return;
  }
  if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
  if (root.nodeType === 1) localizeAttributes(root);
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  let node;
  while ((node = walker.nextNode())) localizeTextNode(node);
  if (root.querySelectorAll) root.querySelectorAll('*').forEach(localizeAttributes);
}

function updateControls() {
  document.querySelectorAll('[data-language-toggle]').forEach((button) => {
    const label = button.querySelector('[data-language-label]');
    if (label) label.textContent = language === 'en' ? 'العربية' : 'English';
    button.setAttribute('aria-label', language === 'en' ? 'Switch language to Arabic' : 'التبديل إلى الإنجليزية');
    button.setAttribute('title', language === 'en' ? 'Switch language to Arabic' : 'التبديل إلى الإنجليزية');
  });
  document.querySelectorAll('[data-font-toggle]').forEach((button) => {
    const label = button.querySelector('[data-font-label]');
    if (label) label.textContent = language === 'en'
      ? (largeText ? 'Standard text' : 'Large text')
      : (largeText ? 'حجم عادي' : 'تكبير النص');
    button.setAttribute('aria-pressed', String(largeText));
    button.setAttribute('aria-label', language === 'en'
      ? (largeText ? 'Use standard text size' : 'Enlarge text')
      : (largeText ? 'استخدام حجم النص العادي' : 'تكبير النص'));
    button.setAttribute('title', language === 'en'
      ? (largeText ? 'Use standard text size' : 'Enlarge text')
      : (largeText ? 'استخدام حجم النص العادي' : 'تكبير النص'));
    button.classList.toggle('active', largeText);
  });
}

export function setLanguage(nextLanguage) {
  language = nextLanguage === 'ar' ? 'ar' : 'en';
  document.documentElement.lang = language;
  document.documentElement.dir = language === 'ar' ? 'rtl' : 'ltr';
  document.documentElement.dataset.language = language;
  try { localStorage.setItem('nlw_language', language); } catch { /* storage may be disabled */ }
  updateControls();
  localizeSubtree(document.head);
  localizeSubtree(document.body);
  window.dispatchEvent(new CustomEvent('nlw:languagechange', { detail: { language } }));
}

export function setLargeText(enabled) {
  largeText = Boolean(enabled);
  document.documentElement.classList.toggle('large-text', largeText);
  try { localStorage.setItem('nlw_large_text', String(largeText)); } catch { /* storage may be disabled */ }
  updateControls();
}

export function getLanguage() {
  return language;
}

export function initI18n() {
  let savedLanguage = 'en';
  let savedLargeText = false;
  try {
    savedLanguage = localStorage.getItem('nlw_language') === 'ar' ? 'ar' : 'en';
    savedLargeText = localStorage.getItem('nlw_large_text') === 'true';
  } catch { /* storage may be disabled */ }

  setLargeText(savedLargeText);
  setLanguage(savedLanguage);

  document.querySelectorAll('[data-language-toggle]').forEach((button) => {
    button.addEventListener('click', () => setLanguage(language === 'en' ? 'ar' : 'en'));
  });
  document.querySelectorAll('[data-font-toggle]').forEach((button) => {
    button.addEventListener('click', () => setLargeText(!largeText));
  });

  if (!observer) {
    observer = new MutationObserver((changes) => {
      changes.forEach((change) => {
        if (change.type === 'characterData') {
          localizeTextNode(change.target);
        } else if (change.type === 'attributes') {
          localizeAttributes(change.target);
        } else {
          change.addedNodes.forEach(localizeSubtree);
        }
      });
    });
    observer.observe(document.body, {
      childList: true,
      characterData: true,
      subtree: true,
      attributes: true,
      attributeFilter: TRANSLATABLE_ATTRIBUTES,
    });
  }
}
