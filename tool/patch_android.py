"""يعدّل مجلد android المولَّد تلقائياً (flutter create) ليدعم:
- صلاحيات الإشعارات POST_NOTIFICATIONS والبصمة
- صلاحيات التخزين الداخلي للنسخ الاحتياطي (MANAGE_EXTERNAL_STORAGE وغيرها)
- MainActivity من نوع FlutterFragmentActivity (مطلوب لـ local_auth)
- Desugaring (مطلوب لـ flutter_local_notifications) و appcompat
- ثيم AppCompat لنافذة البصمة
- minSdk = 24
"""
import pathlib
import re

root = pathlib.Path('android')

# ---------- AndroidManifest ----------
mf = root / 'app/src/main/AndroidManifest.xml'
t = mf.read_text(encoding='utf-8')
perms = [
    'android.permission.POST_NOTIFICATIONS',
    'android.permission.USE_BIOMETRIC',
    'android.permission.RECEIVE_BOOT_COMPLETED',
    'android.permission.VIBRATE',
    'android.permission.ACCESS_FINE_LOCATION',
    'android.permission.ACCESS_COARSE_LOCATION',
    'android.permission.INTERNET',
]
add = ''.join(
    f'    <uses-permission android:name="{p}"/>\n' for p in perms if p not in t
)
# صلاحيات التخزين للنسخ الاحتياطي في مجلد على التخزين الداخلي
storage = [
    ('android.permission.MANAGE_EXTERNAL_STORAGE', ''),
    ('android.permission.READ_EXTERNAL_STORAGE', ' android:maxSdkVersion="32"'),
    ('android.permission.WRITE_EXTERNAL_STORAGE', ' android:maxSdkVersion="29"'),
]
add += ''.join(
    f'    <uses-permission android:name="{p}"{extra}/>\n'
    for p, extra in storage if p not in t
)
t = re.sub(r'(<manifest\b[^>]*>)', lambda m: m.group(1) + '\n' + add, t, count=1)
# أندرويد 10: الوصول للتخزين بالطريقة القديمة
if 'requestLegacyExternalStorage' not in t:
    t = re.sub(r'(<application\b)', r'\1 android:requestLegacyExternalStorage="true"', t, count=1)
t = re.sub(r'android:label="[^"]*"', 'android:label="إدارة العقارات"', t, count=1)
# مفتاح خرائط جوجل (يُمرَّر كمتغير بيئة GOOGLE_MAPS_API_KEY / GitHub secret)
import os
key = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip() or 'MISSING_GOOGLE_MAPS_API_KEY'
if 'com.google.android.geo.API_KEY' not in t:
    t = t.replace('</application>',
        f'    <meta-data android:name="com.google.android.geo.API_KEY" android:value="{key}"/>\n    </application>', 1)
if key == 'MISSING_GOOGLE_MAPS_API_KEY':
    print('WARNING: GOOGLE_MAPS_API_KEY غير مضبوط - الخريطة ستظهر فارغة')
mf.write_text(t, encoding='utf-8')
print('manifest patched')

# ---------- MainActivity -> FlutterFragmentActivity ----------
for f in list(root.rglob('MainActivity.kt')) + list(root.rglob('MainActivity.java')):
    src = f.read_text(encoding='utf-8')
    m = re.search(r'package\s+([\w.]+)', src)
    pkg = m.group(1) if m else 'com.example.real_estate_app'
    if f.suffix == '.kt':
        f.write_text(
            f'package {pkg}\n\nimport io.flutter.embedding.android.FlutterFragmentActivity\n\n'
            'class MainActivity : FlutterFragmentActivity()\n',
            encoding='utf-8',
        )
    else:
        f.write_text(
            f'package {pkg};\n\nimport io.flutter.embedding.android.FlutterFragmentActivity;\n\n'
            'public class MainActivity extends FlutterFragmentActivity {\n}\n',
            encoding='utf-8',
        )
    print('MainActivity patched:', f)

# ---------- app/build.gradle(.kts) ----------
kts = root / 'app/build.gradle.kts'
groovy = root / 'app/build.gradle'
if kts.exists():
    g = kts
    txt = g.read_text(encoding='utf-8')
    txt = re.sub(r'(compileOptions\s*\{)',
                 lambda m: m.group(1) + '\n        isCoreLibraryDesugaringEnabled = true', txt, count=1)
    txt = re.sub(r'minSdk\s*=\s*flutter\.minSdkVersion', 'minSdk = 24', txt)
    txt += (
        '\ndependencies {\n'
        '    coreLibraryDesugaring("com.android.tools:desugar_jdk_libs:2.1.4")\n'
        '    implementation("androidx.appcompat:appcompat:1.7.0")\n'
        '}\n'
    )
else:
    g = groovy
    txt = g.read_text(encoding='utf-8')
    txt = re.sub(r'(compileOptions\s*\{)',
                 lambda m: m.group(1) + '\n        coreLibraryDesugaringEnabled true', txt, count=1)
    txt = re.sub(r'minSdk(Version)?\s*=?\s*flutter\.minSdkVersion', 'minSdkVersion 24', txt)
    txt += (
        '\ndependencies {\n'
        "    coreLibraryDesugaring 'com.android.tools:desugar_jdk_libs:2.1.4'\n"
        "    implementation 'androidx.appcompat:appcompat:1.7.0'\n"
        '}\n'
    )
g.write_text(txt, encoding='utf-8')
print('gradle patched:', g)

# ---------- ثيم AppCompat (نافذة البصمة) ----------
for sx in root.glob('app/src/main/res/values*/styles.xml'):
    s = sx.read_text(encoding='utf-8')
    s2 = re.sub(r'parent="@android:style/Theme\.[\w.]+"',
                'parent="Theme.AppCompat.DayNight.NoActionBar"', s)
    if s2 != s:
        sx.write_text(s2, encoding='utf-8')
        print('styles patched:', sx)
