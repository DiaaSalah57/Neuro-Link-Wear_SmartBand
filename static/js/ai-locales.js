/*
 * Local Arabic display translations for the built-in health narratives.
 * This is a presentation-only phrasebook: it does not modify or call the AI,
 * send readings anywhere, or translate captured patient/contact names.
 */
const TEMPLATES = [
  // Default explanation templates from the existing narrative engine.
  ["The band's accelerometer recorded a sharp impact spike of {accel_mag} g combined with a sudden gyro rotation of {gyro_mag} rad/s — a motion signature strongly consistent with a fall at {time}. Heart rate jumped to {heart_rate} bpm right after impact, which is a typical cardiovascular stress response to a fall.", "سجّل مقياس التسارع في السوار صدمة حادة قدرها {accel_mag} g مع دوران مفاجئ للجيروسكوب قدره {gyro_mag} rad/s — وهو نمط حركة يتوافق بدرجة كبيرة مع السقوط عند {time}. ارتفع معدل ضربات القلب إلى {heart_rate} bpm مباشرة بعد الصدمة، وهي استجابة قلبية وعائية شائعة للسقوط."],
  ["A high-energy impact ({accel_mag} g) with abrupt rotational change ({gyro_mag} rad/s) was detected at {time}. The pattern matches the device's fall-detection model: free-fall-like acceleration followed by a hard landing. Post-event heart rate is {heart_rate} bpm.", "رُصدت صدمة عالية الطاقة ({accel_mag} g) مع تغير دوراني مفاجئ ({gyro_mag} rad/s) عند {time}. يتوافق النمط مع نموذج اكتشاف السقوط في الجهاز: تسارع يشبه السقوط الحر يتبعه ارتطام قوي. معدل ضربات القلب بعد الحدث {heart_rate} bpm."],
  ["Blood oxygen saturation dipped to {spo2}% — below the {spo2_safe}% safety floor set for {name}. SpO2 readings at this level can leave a person feeling breathless, fatigued, or mildly confused, and often worsen overnight when breathing is shallower.", "انخفض تشبع الأكسجين في الدم إلى {spo2}% — دون حد السلامة البالغ {spo2_safe}% المحدد لـ {name}. قد تسبب قراءة SpO₂ بهذا المستوى ضيق التنفس أو الإرهاق أو التشوش الخفيف، وقد تسوء ليلًا عندما يصبح التنفس أقل عمقًا."],
  ["The pulse-oximeter channel reports {spo2}%, a {spo2_drop} point drop below the configured minimum of {spo2_safe}%. For someone with {conditions}, this may indicate shallow breathing, airway obstruction during rest, or a developing chest infection.", "يسجل مقياس التأكسج النبضي {spo2}%، أي انخفاضًا قدره {spo2_drop} نقطة عن الحد الأدنى المحدد {spo2_safe}%. لدى شخص لديه {conditions}، قد يشير ذلك إلى تنفس سطحي أو انسداد مجرى الهواء أثناء الراحة أو بداية التهاب صدري."],
  ["Skin temperature climbed to {temperature}°C, crossing the {temp_safe}°C fever threshold. A sustained rise like this often points to infection or inflammation; combined with the elevated resting heart rate of {heart_rate} bpm it is worth confirming with an oral thermometer.", "ارتفعت حرارة الجلد إلى {temperature}°C، متجاوزة حد الحمّى البالغ {temp_safe}°C. قد يشير استمرار الارتفاع إلى عدوى أو التهاب؛ ومع ارتفاع نبض الراحة إلى {heart_rate} bpm، يُستحسن التأكد بمقياس حرارة فموي."],
  ["The temperature sensor reports {temperature}°C — {temp_delta}°C above {name}'s safe ceiling of {temp_safe}°C. Fever in elderly patients can progress quickly, so this reading should be verified and watched closely over the next few hours.", "يسجل مستشعر الحرارة {temperature}°C — أعلى بـ {temp_delta}°C من الحد الآمن البالغ {temp_safe}°C لـ {name}. قد تتطور الحمّى سريعًا لدى كبار السن، لذا ينبغي التحقق من القراءة ومراقبتها عن كثب خلال الساعات المقبلة."],
  ["Galvanic skin response rose to {gsr} µS while heart-rate variability fell to {hrv} ms — the classic electrodermal signature of acute stress or anxiety. The combined stress index is {stress}/1.00, which is well above {name}'s calm baseline.", "ارتفعت استجابة الجلد الجلفانية إلى {gsr} µS بينما انخفض تباين نبض القلب إلى {hrv} ms — وهي علامة جلدية كهربائية مألوفة للتوتر الحاد أو القلق. بلغ مؤشر التوتر المركب {stress}/1.00، وهو أعلى بكثير من خط الهدوء الأساسي لـ {name}."],
  ["Stress index reached {stress}/1.00: sweat-gland activity ({gsr} µS) is elevated and HRV ({hrv} ms) is suppressed, meaning the sympathetic nervous system ('fight or flight') is dominating. Heart rate is running {hr_delta} bpm above the activity-adjusted expectation.", "بلغ مؤشر التوتر {stress}/1.00: ارتفع نشاط الغدد العرقية ({gsr} µS) وانخفض HRV إلى {hrv} ms، ما يعني هيمنة استجابة الجهاز العصبي الودي («الكر أو الفر»). معدل ضربات القلب أعلى بـ {hr_delta} bpm من المتوقع وفق مستوى النشاط."],
  ["Heart rate surged to {heart_rate} bpm — {hr_delta} bpm above the expected level for the current activity — while the stress index hit {stress}/1.00. This combination of tachycardia, high electrodermal activity ({gsr} µS) and collapsing HRV ({hrv} ms) is consistent with a panic episode or acute distress event.", "قفز معدل ضربات القلب إلى {heart_rate} bpm — أعلى بـ {hr_delta} bpm من المستوى المتوقع للنشاط الحالي — بينما بلغ مؤشر التوتر {stress}/1.00. يتوافق اجتماع تسارع القلب وارتفاع النشاط الجلدي الكهربائي ({gsr} µS) والانخفاض الحاد في HRV ({hrv} ms) مع نوبة هلع أو ضيق حاد."],
  ["A critical stress cascade is underway: {heart_rate} bpm heart rate with stress index {stress}/1.00 and HRV down to {hrv} ms. Symptoms can include chest tightness, trembling and shortness of breath; the pattern requires immediate human attention.", "تجري استجابة توتر حرجة: نبض القلب {heart_rate} bpm، ومؤشر التوتر {stress}/1.00، وHRV عند {hrv} ms. قد تشمل الأعراض ضيق الصدر والارتجاف وضيق التنفس؛ وتتطلب هذه الحالة اهتمامًا بشريًا فوريًا."],
  ["Heart rate is {heart_rate} bpm, above the {hr_safe} bpm comfort ceiling configured for {name}. Persistently elevated pulse can reflect pain, fever, dehydration, arrhythmia or simple overexertion.", "معدل ضربات القلب {heart_rate} bpm، أعلى من الحد المريح البالغ {hr_safe} bpm والمحدد لـ {name}. قد يعكس استمرار ارتفاع النبض ألمًا أو حمّى أو جفافًا أو اضطرابًا في النظم أو إجهادًا بدنيًا."],
  ["The optical heart-rate channel reports {heart_rate} bpm at rest — tachycardia territory for an elderly patient whose ceiling is set to {hr_safe} bpm.", "يسجل مستشعر النبض البصري {heart_rate} bpm أثناء الراحة — وهو مستوى يُعد تسارعًا لدى كبير السن الذي حُدد سقف نبضه عند {hr_safe} bpm."],
  ["Heart rate dropped to {heart_rate} bpm, below the {hr_low_safe} bpm floor. Slow pulse in elderly patients can cause dizziness, fainting or fatigue and should be correlated with how {name} is feeling right now.", "انخفض معدل ضربات القلب إلى {heart_rate} bpm، دون الحد الأدنى البالغ {hr_low_safe} bpm. قد يسبب بطء النبض لدى كبار السن دوخة أو إغماءً أو إرهاقًا؛ وينبغي ربط القراءة بما يشعر به {name} الآن."],
  ["The band recorded {heart_rate} bpm — bradycardia relative to the configured {hr_low_safe} bpm minimum. If this coincides with light-headedness or falls, medical review is recommended.", "سجّل السوار {heart_rate} bpm — وهو بطء في القلب مقارنة بالحد الأدنى المحدد {hr_low_safe} bpm. إذا ترافق ذلك مع دوخة أو سقوط، فيوصى بمراجعة طبية."],
  ["Heart-rate variability has fallen to {hrv} ms with a stress index of {stress}/1.00. Low HRV through the day is a strong marker of physical fatigue, poor recovery or insufficient sleep.", "انخفض تباين نبض القلب إلى {hrv} ms مع مؤشر توتر {stress}/1.00. يُعد انخفاض HRV طوال اليوم مؤشرًا قويًا على الإرهاق البدني أو ضعف التعافي أو قلة النوم."],
  ["HRV of {hrv} ms suggests {name}'s autonomic nervous system is under-recovered. Fatigue like this raises fall risk, so keeping activity gentle is advisable.", "تشير قراءة HRV البالغة {hrv} ms إلى أن الجهاز العصبي اللاإرادي لدى {name} لم يتعافَ بما يكفي. يزيد هذا النوع من الإرهاق خطر السقوط، لذا يُنصح بنشاط خفيف."],
  ["The motion sensors recorded no meaningful movement for {inactive_minutes} minutes during waking hours. Prolonged immobility in elderly patients raises the risk of stiffness, pressure sores, blood clots and unnoticed falls.", "لم تسجل مستشعرات الحركة نشاطًا ملحوظًا لمدة {inactive_minutes} دقيقة خلال ساعات الاستيقاظ. تزيد قلة الحركة الطويلة لدى كبار السن خطر التيبس وقرح الضغط والجلطات والسقوط دون ملاحظة."],
  ["No walking or arm movement has been detected for {inactive_minutes} minutes. If this is unexpected, it may be worth checking on {name} — extended stillness can also follow a fall the band classified as low-energy.", "لم تُكتشف حركة للمشي أو الذراعين لمدة {inactive_minutes} دقيقة. إذا كان ذلك غير متوقع، فتحقق من {name} — فقد يعقب السكون الطويل سقوطٌ صنفه السوار منخفض الشدة."],
  ["The ensemble anomaly model flagged a reading pattern outside {name}'s learned baseline: stress index {stress}/1.00 with heart rate at {heart_rate} bpm and HRV at {hrv} ms. Nothing single-handedly critical, but the combination is atypical.", "رصد نموذج الحالات غير الطبيعية نمط قراءات خارج خط الأساس الذي تعلمه لـ {name}: مؤشر التوتر {stress}/1.00، والنبض {heart_rate} bpm، وHRV عند {hrv} ms. لا توجد قراءة حرجة بمفردها، لكن اجتماعها غير معتاد."],
  ["A mild outlier pattern was detected across multiple channels simultaneously (HR {heart_rate} bpm, HRV {hrv} ms, stress {stress}/1.00). These multi-sensor disagreements are often early signs worth monitoring.", "رُصد نمط شاذ خفيف في عدة قنوات بالتزامن (النبض {heart_rate} bpm، وHRV {hrv} ms، والتوتر {stress}/1.00). قد تكون اختلافات المستشعرات المتعددة إشارات مبكرة تستحق المراقبة."],
  ["The emergency SOS button was triggered manually at {time} from the NeuroLink Wear app. This is a user-initiated distress call and takes priority over all automated detections.", "تم تفعيل زر الاستغاثة SOS يدويًا عند {time} من تطبيق NeuroLink Wear. هذا طلب مساعدة بدأه المستخدم وله الأولوية على جميع الاكتشافات التلقائية."],
  ["A one-press SOS was activated at {time}. Wearer GPS position at activation is being shared with the dispatch list.", "تم تفعيل الاستغاثة بلمسة واحدة عند {time}. تتم مشاركة موقع GPS لمرتدي السوار مع قائمة الإخطار."],

  // Existing seeded incident and summary titles.
  ["Fall detected in living room — hard impact {impact} g", "تم اكتشاف سقوط في غرفة المعيشة — صدمة قوية {impact} g"],
  ["Overnight desaturation — SpO2 {spo2}%", "انخفاض الأكسجين ليلًا — SpO₂ {spo2}%"],
  ["High stress episode — index {index}", "نوبة توتر مرتفع — المؤشر {index}"],
  ["Fever — {temperature}°C", "حمّى — {temperature}°C"],
  ["No movement for {minutes} minutes", "لا توجد حركة لمدة {minutes} دقيقة"],
  ["Daily health summary — {name}", "ملخص الصحة اليومي — {name}"],
  ["Fall incident analysis — {time}", "تحليل حادث السقوط — {time}"],
  ["Weekly outlook — week to date", "نظرة أسبوعية — ملخص هذا الأسبوع"],

  // Existing seeded incident narratives (names/medical details are captured as-is).
  ["The band's accelerometer recorded a sharp impact spike of {accel} g combined with a sudden gyro rotation of {gyro} rad/s at {time} — a motion signature strongly consistent with a fall while {name} was walking from the armchair to the kitchen. Heart rate jumped to {hr} bpm right after impact, a typical cardiovascular stress response to a fall.", "سجّل مقياس التسارع في السوار صدمة حادة قدرها {accel} g مع دوران مفاجئ للجيروسكوب قدره {gyro} rad/s عند {time} — وهو نمط يتوافق بدرجة كبيرة مع السقوط أثناء مشي {name} من الكرسي إلى المطبخ. ارتفع نبض القلب إلى {hr} bpm مباشرة بعد الصدمة، وهي استجابة قلبية وعائية شائعة للسقوط."],
  ["The pulse-oximeter channel reports {spo2}%, a {drop} point drop below the configured minimum of {safe}%. For someone with {conditions}, this may indicate shallow breathing during light sleep or a developing chest infection. The episode lasted roughly {duration} minutes before recovering.", "يسجل مقياس التأكسج النبضي {spo2}%، أي انخفاضًا قدره {drop} نقطة عن الحد الأدنى المحدد {safe}%. لدى شخص لديه {conditions}، قد يشير ذلك إلى تنفس سطحي أثناء النوم الخفيف أو بداية التهاب صدري. استمرت الحالة نحو {duration} دقيقة قبل التحسن."],
  ["Galvanic skin response rose to {gsr} µS while heart-rate variability fell to {hrv} ms — the classic electrodermal signature of acute stress or anxiety. The combined stress index reached {stress}/1.00, well above {name}'s calm baseline, during the physiotherapy session yesterday afternoon.", "ارتفعت استجابة الجلد الجلفانية إلى {gsr} µS بينما انخفض تباين نبض القلب إلى {hrv} ms — وهي علامة جلدية كهربائية مألوفة للتوتر الحاد أو القلق. بلغ مؤشر التوتر المركب {stress}/1.00، أعلى بكثير من خط الهدوء الأساسي لـ {name}، خلال جلسة العلاج الطبيعي بعد ظهر أمس."],
  ["Skin temperature climbed to {temperature}°C, crossing the {safe}°C fever threshold. A sustained rise like this often points to infection or inflammation; combined with the elevated resting heart rate of {hr} bpm it was worth confirming with an oral thermometer — the caregiver confirmed {oral}°C orally {minutes} minutes later.", "ارتفعت حرارة الجلد إلى {temperature}°C، متجاوزة حد الحمّى البالغ {safe}°C. قد يشير استمرار الارتفاع إلى عدوى أو التهاب؛ ومع ارتفاع نبض الراحة إلى {hr} bpm، كان من الأفضل التأكد بمقياس فموي — وقد أكد مقدم الرعاية قراءة {oral}°C بعد {minutes} دقيقة."],
  ["The motion sensors recorded no meaningful movement for {minutes} minutes during waking hours. Prolonged immobility in elderly patients raises the risk of stiffness, pressure sores, blood clots and unnoticed falls. The caregiver check-in confirmed {name} was reading in the garden.", "لم تسجل مستشعرات الحركة نشاطًا ملحوظًا لمدة {minutes} دقيقة خلال ساعات الاستيقاظ. تزيد قلة الحركة الطويلة لدى كبار السن خطر التيبس وقرح الضغط والجلطات والسقوط دون ملاحظة. أكد التحقق من مقدم الرعاية أن {name} كان يقرأ في الحديقة."],

  // Daily-summary sentences produced by the built-in summary engine.
  ["{name} wore the band for {intervals} monitored intervals.", "ارتدى {name} السوار خلال {intervals} فترة مراقبة."],
  ["Average heart rate was {average} bpm ({night} bpm overnight vs {day} bpm during the day), with heart-rate variability averaging {hrv} ms.", "بلغ متوسط نبض القلب {average} bpm (‏{night} bpm ليلًا مقابل {day} bpm نهارًا)، وبلغ متوسط تباين النبض {hrv} ms."],
  ["Oxygen saturation dipped to {spo2}% at its lowest point — a brief overnight desaturation that is common in light sleep, but worth repeating if it recurs.", "انخفض تشبع الأكسجين إلى {spo2}% عند أدنى مستوى — وهو انخفاض ليلي قصير شائع أثناء النوم الخفيف، لكن يُستحسن إعادة التحقق إذا تكرر."],
  ["Blood oxygen stayed reassuringly stable (minimum {spo2}%).", "ظل أكسجين الدم مستقرًا بصورة مطمئنة (الحد الأدنى {spo2}%)."],
  ["Skin temperature peaked at {temperature}°C — slightly elevated, keep an eye on it.", "بلغت حرارة الجلد ذروتها عند {temperature}°C — وهي مرتفعة قليلًا، لذا تجب مراقبتها."],
  ["Temperature remained in the normal band (peak {temperature}°C).", "بقيت الحرارة ضمن النطاق الطبيعي (الذروة {temperature}°C)."],
  ["Stress index reached {stress} during the day — a clear episode that resolved afterwards.", "بلغ مؤشر التوتر {stress} خلال النهار — وهي نوبة واضحة انتهت لاحقًا."],
  ["Breathing exercises before stressful activities may help.", "قد تساعد تمارين التنفس قبل الأنشطة المسببة للتوتر."],
  ["Stress markers stayed low throughout the day, indicating good emotional regulation.", "ظلت مؤشرات التوتر منخفضة طوال اليوم، مما يشير إلى استقرار عاطفي جيد."],
  ["{count} fall event(s) were recorded today.", "سُجلت {count} حالة سقوط اليوم."],
  ["Assistive mobility review is recommended.", "يوصى بمراجعة وسائل المساعدة على الحركة."],
  ["No falls were detected.", "لم يُكتشف أي سقوط."],
  ["Overall outlook for tomorrow is positive: keep hydration and the evening walk routine.", "التوقعات العامة ليوم غد إيجابية: حافظ على شرب السوائل وروتين المشي المسائي."],
  ["Tomorrow looks stable — protect the evening rest window to keep HRV trending up.", "يبدو الغد مستقرًا — حافظ على فترة الراحة المسائية لدعم تحسن HRV."],
  ["The trend is mildly improving; consistency in medication timing will help keep it that way.", "يتحسن الاتجاه قليلًا؛ ويساعد الانتظام في مواعيد الأدوية على استمرار ذلك."],

  // Built-in recommendations. Placeholders keep all personal names unchanged.
  ["Call {name} immediately — if there is no answer within 60 seconds, send someone to the location on the map.", "اتصل بـ {name} فورًا — إذا لم يرد خلال 60 ثانية، أرسل شخصًا إلى الموقع على الخريطة."],
  ["Do not ask {name} to get up unassisted; falls in elderly patients are frequently followed by a second fall.", "لا تطلب من {name} النهوض دون مساعدة؛ فكثيرًا ما يتبع السقوط لدى كبار السن سقوطٌ آخر."],
  ["If there is head impact, confusion, or pain in the hip/wrist, arrange medical evaluation today.", "إذا حدث ارتطام بالرأس أو تشوش أو ألم في الورك أو الرسغ، فرتّب تقييمًا طبيًا اليوم."],
  ["Dispatch the nearest emergency contact now and share the live GPS link.", "أخطر أقرب جهة اتصال للطوارئ الآن وشارك رابط GPS المباشر."],
  ["Keep {name} still and warm while help is arranged; check for bleeding or limb deformity.", "أبقِ {name} ساكنًا ودافئًا أثناء ترتيب المساعدة؛ وتحقق من وجود نزيف أو تشوه في أحد الأطراف."],
  ["Log the incident time and circumstances for the physician review.", "سجّل وقت الحادث وظروفه لمراجعتها من قبل الطبيب."],
  ["Encourage slow deep breathing and sit {name} upright — upright posture opens the diaphragm.", "شجّع التنفس البطيء والعميق وأجلس {name} بوضع مستقيم — فهذا يساعد على تمدد الحجاب الحاجز."],
  ["Re-check SpO2 after 5 minutes of rest; if it stays below {spo2_safe}%, contact the physician.", "أعد فحص SpO₂ بعد 5 دقائق من الراحة؛ إذا بقي دون {spo2_safe}%، فاتصل بالطبيب."],
  ["Ensure the room is ventilated and check that nothing is obstructing the band's sensor against the skin.", "تأكد من تهوية الغرفة ومن عدم وجود ما يحجب مستشعر السوار عن الجلد."],
  ["Move to fresh air or open a window and re-measure in a few minutes.", "انتقل إلى هواء نقي أو افتح نافذة وأعد القياس بعد بضع دقائق."],
  ["If {name} reports breathlessness, confusion or chest pain, escalate to emergency services immediately.", "إذا أبلغ {name} عن ضيق تنفس أو تشوش أو ألم في الصدر، فاتصل بخدمات الطوارئ فورًا."],
  ["Review COPD/asthma inhaler availability if oxygen does not recover within 10 minutes.", "تحقق من توفر بخاخ الانسداد الرئوي أو الربو إذا لم يتحسن الأكسجين خلال 10 دقائق."],
  ["Confirm with an oral or tympanic thermometer and encourage fluid intake.", "تأكد بمقياس حرارة فموي أو طبلي وشجّع على شرب السوائل."],
  ["Monitor temperature every 30–60 minutes; if it exceeds 38.5°C or persists over 12 hours, contact the GP.", "راقب الحرارة كل 30–60 دقيقة؛ وإذا تجاوزت 38.5°C أو استمرت أكثر من 12 ساعة، فاتصل بالطبيب العام."],
  ["Watch for accompanying symptoms: shivering, confusion, reduced urination or a new cough.", "راقب الأعراض المصاحبة مثل القشعريرة أو التشوش أو قلة التبول أو السعال الجديد."],
  ["Offer fluids and keep the room comfortably cool; avoid heavy blankets.", "قدّم السوائل وحافظ على برودة مريحة في الغرفة؛ وتجنب الأغطية الثقيلة."],
  ["Record the fever episode in the symptom log for the next medical review.", "سجّل نوبة الحمّى في سجل الأعراض لمراجعتها طبيًا لاحقًا."],
  ["If {name} is on blood thinners or immunosuppressants, call the care team today — fever thresholds are lower for these patients.", "إذا كان {name} يتناول مميعات الدم أو مثبطات المناعة، فاتصل بفريق الرعاية اليوم — فحدود الحمّى تكون أقل لدى هؤلاء المرضى."],
  ["Guide {name} through slow paced breathing (4 seconds in, 6 seconds out) for 2–3 minutes.", "ساعد {name} على التنفس ببطء وانتظام (شهيق 4 ثوانٍ وزفير 6 ثوانٍ) لمدة 2–3 دقائق."],
  ["Reduce stimulation: quiet room, seated posture, reassuring conversation.", "خفف المثيرات: غرفة هادئة، وجلوس مريح، وحديث مطمئن."],
  ["If stress index stays above 0.60 for more than 20 minutes, check for pain, caffeine or a distressing trigger.", "إذا بقي مؤشر التوتر أعلى من 0.60 لأكثر من 20 دقيقة، فتحقق من وجود ألم أو تناول كافيين أو سبب للضيق."],
  ["Suggest a short calm activity — tea, music or a gentle walk in the corridor.", "اقترح نشاطًا هادئًا قصيرًا — شايًا أو موسيقى أو مشيًا خفيفًا في الممر."],
  ["Re-check HRV after 10 minutes of rest; recovery is the goal, not just a lower heart rate.", "أعد فحص HRV بعد 10 دقائق من الراحة؛ فالهدف هو التعافي، وليس خفض نبض القلب فقط."],
  ["Repeated stress spikes this week should be mentioned at the next clinical review.", "ينبغي ذكر تكرار ارتفاعات التوتر هذا الأسبوع في المراجعة الطبية القادمة."],
  ["Stay on a voice call with {name} — calm, steady contact is the fastest intervention.", "ابقَ على اتصال صوتي مع {name} — فالتواصل الهادئ والمستمر هو أسرع تدخل."],
  ["Coach breathing: inhale 4 s, exhale 6 s; ground by naming 5 visible objects in the room.", "وجّه التنفس: شهيق 4 ثوانٍ وزفير 6 ثوانٍ؛ وساعد على التركيز بذكر 5 أشياء مرئية في الغرفة."],
  ["If chest pain, fainting or blue lips appear, escalate to emergency services immediately.", "إذا ظهر ألم في الصدر أو إغماء أو ازرقاق الشفتين، فاتصل بالطوارئ فورًا."],
  ["Remind {name} the episode will pass; panics typically peak within 10 minutes.", "ذكّر {name} بأن النوبة ستمر؛ فعادةً تبلغ نوبات الهلع ذروتها خلال 10 دقائق."],
  ["Avoid stimulants (caffeine, nicotine) for the rest of the day.", "تجنب المنبهات (الكافيين والنيكوتين) لبقية اليوم."],
  ["Book a GP follow-up if panic episodes repeat within a week — medication review may be warranted.", "احجز موعد متابعة مع الطبيب العام إذا تكررت نوبات الهلع خلال أسبوع — فقد يلزم مراجعة الأدوية."],
  ["Pause physical activity and sit {name} down with legs elevated slightly.", "أوقف النشاط البدني وأجلس {name} مع رفع الساقين قليلًا."],
  ["Re-measure after 5 minutes of stillness; if heart rate stays above {hr_safe} bpm, contact the care team.", "أعد القياس بعد 5 دقائق من السكون؛ إذا بقي النبض أعلى من {hr_safe} bpm، فاتصل بفريق الرعاية."],
  ["Check hydration and recent caffeine or medication changes.", "تحقق من شرب السوائل ومن أي تغييرات حديثة في الكافيين أو الأدوية."],
  ["Look for triggers: fever, pain, dehydration or missed heart medication.", "ابحث عن أسباب محتملة: الحمّى أو الألم أو الجفاف أو نسيان دواء القلب."],
  ["If accompanied by chest pain or faintness, treat as a cardiac event and escalate.", "إذا ترافق ذلك مع ألم في الصدر أو شعور بالإغماء، فتعامل معه كحالة قلبية وصعّد الاستجابة."],
  ["Ask {name} how they feel: dizziness, near-fainting or fatigue need medical attention.", "اسأل {name} عن شعوره: فالدوخة أو اقتراب الإغماء أو الإرهاق تستدعي عناية طبية."],
  ["Avoid sudden standing; assist with mobility until the pulse recovers.", "تجنب الوقوف المفاجئ؛ وساعد على الحركة حتى يعود النبض إلى مستواه الطبيعي."],
  ["If heart rate stays under {hr_low_safe} bpm for more than 10 minutes or symptoms appear, contact the physician.", "إذا بقي النبض أقل من {hr_low_safe} bpm لأكثر من 10 دقائق أو ظهرت أعراض، فاتصل بالطبيب."],
  ["Check whether beta-blockers or other rate-slowing medication was taken recently.", "تحقق مما إذا تم تناول حاصرات بيتا أو أدوية أخرى تُبطئ النبض مؤخرًا."],
  ["Keep {name} seated and hydrated; re-check in 5 minutes.", "أبقِ {name} جالسًا مع شرب السوائل؛ وأعد الفحص بعد 5 دقائق."],
  ["Prioritise rest today; keep walks short and supported.", "اجعل الراحة أولوية اليوم؛ ولتكن فترات المشي قصيرة مع المساندة."],
  ["A light meal and fluids can help recovery — fatigue plus low HRV often tracks with dehydration.", "قد تساعد وجبة خفيفة وسوائل على التعافي — فالإرهاق مع انخفاض HRV يرتبط غالبًا بالجفاف."],
  ["Protect against falls: clear walking paths and assist with stairs.", "قلل خطر السقوط: أخلِ مسارات المشي وساعد عند استخدام الدرج."],
  ["Encourage an early night; recovery sleep is the most effective intervention.", "شجّع على النوم مبكرًا؛ فالنوم التعويضي من أكثر وسائل التعافي فاعلية."],
  ["If fatigue persists more than 48 hours, mention it at the next GP visit.", "إذا استمر الإرهاق أكثر من 48 ساعة، فاذكره في الزيارة القادمة للطبيب العام."],
  ["Send a quick check-in message or call — confirm {name} is okay and simply resting.", "أرسل رسالة للاطمئنان أو اتصل — وتأكد أن {name} بخير ويستريح فحسب."],
  ["If there is no response within 10 minutes, treat as a potential fall or medical event and dispatch help.", "إذا لم يصل رد خلال 10 دقائق، فتعامل مع الأمر كاحتمال سقوط أو حالة طبية وأرسل المساعدة."],
  ["Encourage a short assisted walk; gentle movement reduces stiffness and clot risk.", "شجّع على مشي قصير بمساعدة؛ فالحركة الخفيفة تقلل التيبس وخطر الجلطات."],
  ["Verify the band is being worn — an unattended band on a table also produces long still periods.", "تحقق من ارتداء السوار — فتركه على الطاولة قد يُظهر فترات سكون طويلة أيضًا."],
  ["If quiet time is intentional (nap, reading), you can snooze this alert type in thresholds.", "إذا كان السكون مقصودًا (قيلولة أو قراءة)، يمكنك إيقاف هذا النوع من التنبيه مؤقتًا من إعدادات الحدود."],
  ["Keep an eye on {name} over the next hour and re-check the live dashboard.", "راقب {name} خلال الساعة القادمة وأعد التحقق من لوحة المتابعة المباشرة."],
  ["Note any symptoms reported by the wearer for the next medical review.", "دوّن أي أعراض يذكرها مرتدي السوار لمراجعتها طبيًا لاحقًا."],
  ["If the anomaly repeats, tighten the alert thresholds or contact the care team.", "إذا تكررت الحالة غير الطبيعية، فشدّد حدود التنبيه أو تواصل مع فريق الرعاية."],
  ["No immediate intervention is required, but avoid strenuous activity until readings stabilise.", "لا يلزم تدخل فوري، لكن تجنب النشاط المجهد حتى تستقر القراءات."],
  ["A brief call to confirm wellbeing is a proportionate response.", "اتصال قصير للاطمئنان على الحالة استجابة مناسبة."],
  ["Acknowledge the call and dispatch the emergency contact list now.", "أكّد استلام النداء وأخطر جهات اتصال الطوارئ الآن."],
  ["Keep a voice line open with {name} until help arrives.", "ابقَ على اتصال صوتي مع {name} حتى وصول المساعدة."],
  ["Share the live GPS position with responders and record arrival times.", "شارك موقع GPS المباشر مع فرق الاستجابة وسجّل أوقات الوصول."],
  ["Send someone to the location on the map immediately — do not wait for callback.", "أرسل شخصًا إلى الموقع على الخريطة فورًا — ولا تنتظر إعادة الاتصال."],
  ["Prepare to give responders the medication list and medical history card.", "جهّز قائمة الأدوية والبطاقة الطبية لتقديمها إلى فرق الاستجابة."],
];

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function templateRegExp(template) {
  const placeholder = /\{([a-z0-9_]+)\}/gi;
  let cursor = 0;
  let expression = '^';
  let match;
  while ((match = placeholder.exec(template))) {
    expression += escapeRegExp(template.slice(cursor, match.index));
    expression += `(?<${match[1]}>.+?)`;
    cursor = match.index + match[0].length;
  }
  expression += `${escapeRegExp(template.slice(cursor))}$`;
  return new RegExp(expression, 'i');
}

const COMPILED = TEMPLATES.map(([source, target]) => ({ regex: templateRegExp(source), target }));

function translateOneKnownPhrase(source) {
  for (const { regex, target } of COMPILED) {
    const match = source.match(regex);
    if (!match) continue;
    return target.replace(/\{([a-z0-9_]+)\}/gi, (_, key) => match.groups?.[key] ?? `{${key}}`);
  }
  return null;
}

/** Translate known local alert/summary text while retaining captured names and readings. */
export function translateKnownClinicalText(text) {
  const source = String(text ?? '').trim().replace(/\s+/g, ' ');
  const whole = translateOneKnownPhrase(source);
  if (whole) return whole;

  // Daily summaries are assembled from short built-in sentences. Translate
  // recognized sentences individually, leaving unfamiliar/user-authored text intact.
  const sentences = source.split(/(?<=[.!?])\s+(?=[A-Z])/);
  if (sentences.length < 2) return null;
  let changed = false;
  const translated = sentences.map((sentence) => {
    const result = translateOneKnownPhrase(sentence);
    if (result) changed = true;
    return result || sentence;
  });
  return changed ? translated.join(' ') : null;
}
