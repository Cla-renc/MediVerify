import random
from django.core.management import call_command
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.products.models import Manufacturer, Product, Batch, UnitCode
from apps.inventory.models import Pharmacy, InventoryItem
from apps.verification.models import VerificationScan, CloneAlert
from apps.reports.models import SuspiciousReport, SystemSettings

User = get_user_model()

class Command(BaseCommand):
    help = "Seeds database with manufacturers, products, batches, pharmacies, inventory, and sample scans for MediVerify."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting MediVerify database seeding..."))

        # 1. System Settings
        settings_obj = SystemSettings.get_settings()
        settings_obj.max_scan_threshold = 3
        settings_obj.max_velocity_kmh = 800.0
        settings_obj.distinct_ip_window_minutes = 15
        settings_obj.distinct_ip_threshold = 3
        settings_obj.save()

        # 2. Users & Roles
        regulator_user, _ = User.objects.get_or_create(
            username="regulator",
            defaults={
                "email": "regulator@ppb.go.ke",
                "role": "REGULATOR",
                "phone_number": "+254700000001",
                "organization_name": "Pharmacy and Poisons Board Kenya",
                "is_staff": True,
                "is_superuser": True
            }
        )
        regulator_user.set_password("admin123")
        regulator_user.save()

        mfg_users_data = [
            ("cosmos_mfg", "info@cosmos-pharm.co.ke", "Cosmos Limited Kenya"),
            ("dawa_mfg", "contact@dawa.co.ke", "Dawa Pharmaceuticals Ltd"),
            ("beta_mfg", "support@betaheadcare.co.ke", "Beta Healthcare International")
        ]

        mfg_objs = []
        for username, email, org in mfg_users_data:
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": email, "role": "MANUFACTURER", "organization_name": org, "phone_number": "+254722111222"}
            )
            u.set_password("pass123")
            u.save()

            mfg, _ = Manufacturer.objects.get_or_create(
                user=u,
                defaults={
                    "license_number": f"MFG-PPB-{username.upper()}",
                    "name": org,
                    "country": "Kenya",
                    "contact_email": email,
                    "is_verified": True,
                },
            )
            mfg_objs.append(mfg)

        # 3. Pharmacies & Pharmacist Users
        pharmacy_data = [
            ("nairobi_pharm", "Nairobi City Pharmacy", "P1001", "Kenyatta Ave, CBD", "Nairobi", -1.286389, 36.817223, 98.0, "TRUSTED"),
            ("mombasa_pharm", "Coast Medical Supplies", "P1002", "Nkrumah Rd, Town", "Mombasa", -4.043477, 39.668206, 92.0, "TRUSTED"),
            ("kisumu_pharm", "Lakeside Chemist", "P1003", "Odinga Oginga Rd", "Kisumu", -0.091702, 34.767956, 75.0, "WATCH"),
            ("nakuru_pharm", "Rift Valley Pharmacy", "P1004", "Kenyatta Ave", "Nakuru", -0.303099, 36.080026, 96.0, "TRUSTED"),
            ("eldoret_pharm", "Highland Healthcare", "P1005", "Uganda Rd", "Uasin Gishu", 0.514277, 35.269780, 42.0, "FLAGGED")
        ]

        pharmacy_objs = []
        for username, name, lic, addr, county, lat, lng, score, rating in pharmacy_data:
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@pharmacy.co.ke", "role": "PHARMACIST", "organization_name": name}
            )
            u.set_password("pass123")
            u.save()

            p, _ = Pharmacy.objects.get_or_create(
                license_number=lic,
                defaults={
                    "user": u,
                    "name": name,
                    "address": addr,
                    "county": county,
                    "latitude": lat,
                    "longitude": lng,
                    "trust_score": score,
                    "trust_rating": rating
                }
            )
            pharmacy_objs.append(p)

        # 4. Products (15 Products across the 3 Manufacturers)
        products_catalog = [
            # Cosmos Ltd
            (mfg_objs[0], "Paracetamol Cosmos", "Paracetamol", "Tablet", "500mg", "Analgesic",
             "Take 1 to 2 tablets every 4 to 6 hours as needed. Maximum 8 tablets in 24 hours.",
             "Kunywa vidonge 1 au 2 kila baada ya masaa 4 hadi 6 inavyohitajika. Isizidi vidonge 8 kwa siku.",
             "Mild nausea, skin rash, or allergic reactions.",
             "Kichefuchefu kidogo, vipele kwenye ngozi, au mzio.",
             "Do not exceed recommended dose. Do not take with other paracetamol products.",
             "Usizidishe kipimo kilichopendekezwa. Usinywe na dawa zingine zenye paracetamol."),
            (mfg_objs[0], "CosmoCillin", "Amoxicillin", "Capsule", "500mg", "Antibiotic",
             "Take 1 capsule 3 times daily for 7 days with water.",
             "Kunywa kidonge 1 mara 3 kwa siku kwa siku 7 na maji.",
             "Nausea, diarrhea, stomach upset, skin rash.",
             "Kichefuchefu, kuhara, kuumwa na tumbo, vipele.",
             "Complete the full prescribed course even if symptoms disappear.",
             "Maliza kozi nzima hata kama dalili zitapotea."),
            (mfg_objs[0], "Cosmofen", "Ibuprofen", "Tablet", "400mg", "Anti-inflammatory",
             "Take 1 tablet after meals 3 times a day.",
             "Kunywa kidonge 1 baada ya kula mara 3 kwa siku.",
             "Stomach pain, heartburn, dizziness.",
             "Tumbo kuuma, kiungulia, kizunguzungu.",
             "Take with food or milk to prevent gastric irritation.",
             "Kunywa pamoja na chakula au maziwa kuzuia tumbo kuuma."),
            (mfg_objs[0], "CosmoTab Cef", "Cefuroxime", "Tablet", "250mg", "Antibiotic",
             "Take 1 tablet every 12 hours after food for 5 to 10 days.",
             "Kunywa kidonge 1 kila masaa 12 baada ya chakula kwa siku 5 hadi 10.",
             "Mild diarrhea, nausea, headache.",
             "Kuhara kidogo, kichefuchefu, kichwa kuuma.",
             "Inform doctor if you have history of penicillin allergy.",
             "Mfahamishe daktari kama una mzio wa penicillin."),
            (mfg_objs[0], "CosmoSal Inhaler", "Salbutamol", "Inhaler", "100mcg", "Respiratory",
             "Inhale 1 to 2 puffs when experiencing shortness of breath.",
             "Vuta pumzi mara 1 au 2 unapohisi kubanwa na kifua.",
             "Mild tremors, rapid heartbeat, headache.",
             "Teteteko la mikono, moyo kwenda mbio, kichwa kuuma.",
             "Keep inhaler readily accessible. Consult doctor if relief lasts less than 3 hours.",
             "Weka kifaa karibu nawe. Muone daktari kama nafuu haidumu zaidi ya masaa 3."),

            # Dawa Ltd
            (mfg_objs[1], "Dawa-Moja", "Paracetamol Extra", "Tablet", "500mg/65mg", "Analgesic",
             "Take 2 tablets up to 4 times daily for severe pain.",
             "Kunywa vidonge 2 mara 4 kwa siku kwa maumivu makali.",
             "Insomnia, restlessness due to caffeine content.",
             "Kutopata giấc / usingizi, kutotulia kwa sababu ya caffeine.",
             "Avoid taking close to bedtime. Not recommended for young children.",
             "Kaa mbali na kunywa kabla ya kulala. Haipendekezwi kwa watoto wadogo."),
            (mfg_objs[1], "DawaMet", "Metformin", "Tablet", "500mg", "Antidiabetic",
             "Take 1 tablet twice daily with morning and evening meals.",
             "Kunywa kidonge 1 mara 2 kwa siku na chakula cha asubuhi na jioni.",
             "Nausea, metallic taste, abdominal bloating.",
             "Kichefuchefu, ladha ya chuma mdomoni, tumbo kujaa upepo.",
             "Do not stop medication without consulting your physician.",
             "Usiache kutumia dawa bila ushauri wa daktari."),
            (mfg_objs[1], "Dawa-Coartem", "Artemether / Lumefantrine", "Tablet", "20mg/120mg", "Anti-Malarial",
             "Take 4 tablets initially, 4 tablets after 8 hours, then 4 tablets twice daily for 2 days.",
             "Kunywa vidonge 4 kwanza, 4 baada ya masaa 8, kisha 4 mara mbili kwa siku kwa siku 2.",
             "Loss of appetite, dizziness, fatigue, joint pain.",
             "Kukosa hamu ya kula, kizunguzungu, uchovu, viungo kuuma.",
             "Must be taken with fatty food or milk for full absorption.",
             "Lazima inywewe na chakula chenye mafuta au maziwa ili ifanye kazi vizuri."),
            (mfg_objs[1], "Dawamox Suspension", "Amoxicillin Liquid", "Syrup", "125mg/5ml", "Pediatric Antibiotic",
             "Give child 5ml every 8 hours for 7 days.",
             "Mpe mtoto 5ml kila masaa 8 kwa siku 7.",
             "Mild diarrhea, diaper rash.",
             "Kuhara kidogo, vipele vya nepi.",
             "Shake bottle thoroughly before every dose. Keep refrigerated.",
             "Tikisa chupa vizuri kabla ya kumpa mtoto. Weka kwenye jokofu."),
            (mfg_objs[1], "DawaCet", "Cetirizine", "Tablet", "10mg", "Antihistamine",
             "Take 1 tablet once daily at night.",
             "Kunywa kidonge 1 mara moja kwa siku usiku.",
             "Drowsiness, dry mouth.",
             "Hali ya usinzi, mdomo kukauka.",
             "May cause drowsiness. Avoid driving or operating machinery after taking.",
             "Inaweza kuleta usinzi. Usiendeshe gari baada ya kunywa."),

            # Beta Healthcare
            (mfg_objs[2], "Mara-Moja Action", "Aspirin + Paracetamol", "Tablet", "400mg/200mg", "Analgesic",
             "Dissolve 1 to 2 tablets in half a glass of water for fast relief.",
             "Yeyusha vidonge 1 au 2 kwa nusu glasi ya maji kwa nafuu ya haraka.",
             "Gastric irritation, ringing in ears.",
             "Tumbo kuuma, sauti masikioni.",
             "Contraindicated in children under 16 years and ulcer patients.",
             "Haifai kwa watoto chini ya miaka 16 na walio na vidonda vya tumbo."),
            (mfg_objs[2], "Beta-Omeprazole", "Omeprazole", "Capsule", "20mg", "Gastrointestinal",
             "Take 1 capsule daily 30 minutes before breakfast with water.",
             "Kunywa kidonge 1 kila siku masaa nusu kabla ya kifua kinywaji cha asubuhi.",
             "Headache, constipation, gas.",
             "Kichwa kuuma, choo kugumu, gesi tumboni.",
             "Swallow capsule whole; do not chew or crush.",
             "Meza kidonge kizima; usichafune wala kusaga."),
            (mfg_objs[2], "Beta-Azithro", "Azithromycin", "Tablet", "500mg", "Antibiotic",
             "Take 1 tablet once daily for 3 days 1 hour before or 2 hours after meals.",
             "Kunywa kidonge 1 mara 1 kwa siku kwa siku 3 kabla au baada ya chakula.",
             "Mild stomach cramps, nausea, diarrhea.",
             "Tumbo kukata, kichefuchefu, kuhara.",
             "Report severe abdominal pain or persistent diarrhea immediately.",
             "Ripoti maumivu makali ya tumbo au kuhara kusiokoma mara moja."),
            (mfg_objs[2], "Beta-Cipro", "Ciprofloxacin", "Tablet", "500mg", "Antibiotic",
             "Take 1 tablet twice daily for 5 to 7 days with plenty of water.",
             "Kunywa kidonge 1 mara 2 kwa siku kwa siku 5 hadi 7 na maji mengi.",
             "Nausea, tendon discomfort, photosensitivity.",
             "Kichefuchefu, miguu au viungo kuuma, kutoingiliana na mwanga wa jua.",
             "Avoid antacids containing calcium or magnesium 2 hours before or after taking.",
             "Epuka dawa za kiungulia zenye calcium masaa 2 kabla au baada ya kunywa."),
            (mfg_objs[2], "Beta-Flagyl", "Metronidazole", "Tablet", "400mg", "Antiprotozoal",
             "Take 1 tablet 3 times daily with meals for 5 to 7 days.",
             "Kunywa kidonge 1 mara 3 kwa siku na chakula kwa siku 5 hadi 7.",
             "Metallic taste, dark urine, nausea.",
             "Ladha ya chuma, mkojo kuwa mweusi, kichefuchefu.",
             "STRICTLY AVOID ALCOHOL during treatment and for 48 hours after.",
             "EPUKA POMBE KABISA wakati wa matibabu na kwa masaa 48 baada ya kumaliza.")
        ]

        product_objs = []
        for mfg, brand, gen, dosage, strength, cat, u_en, u_sw, s_en, s_sw, w_en, w_sw in products_catalog:
            p, _ = Product.objects.get_or_create(
                brand_name=brand,
                manufacturer=mfg,
                defaults={
                    "generic_name": gen,
                    "dosage_form": dosage,
                    "strength": strength,
                    "category": cat,
                    "usage_instructions_en": u_en,
                    "usage_instructions_sw": u_sw,
                    "side_effects_en": s_en,
                    "side_effects_sw": s_sw,
                    "key_warnings_en": w_en,
                    "key_warnings_sw": w_sw,
                }
            )
            product_objs.append(p)

        # 5. Batches (30 Batches: Valid, Expiring in 30/60/90 days, Expired, and Recalled)
        today = timezone.now().date()
        batch_objs = []
        
        for idx, prod in enumerate(product_objs):
            # Create 2 batches per product = 30 total batches
            # Batch A: Valid / Future expiry
            b_num_a = f"BN-{prod.brand_name[:3].upper()}-2026-A{idx+10}"
            m_date_a = today - timedelta(days=120)
            e_date_a = today + timedelta(days=365) # Valid 1 year
            
            batch_a, _ = Batch.objects.get_or_create(
                batch_number=b_num_a,
                defaults={
                    "product": prod,
                    "manufacture_date": m_date_a,
                    "expiry_date": e_date_a,
                    "total_quantity": 500,
                    "is_recalled": False
                }
            )
            batch_objs.append(batch_a)

            # Batch B: Special state (Expiring soon, Expired, or Recalled)
            b_num_b = f"BN-{prod.brand_name[:3].upper()}-2025-B{idx+10}"
            m_date_b = today - timedelta(days=300)
            
            if idx == 0:
                # Recalled Batch!
                e_date_b = today + timedelta(days=180)
                is_recalled = True
                recall_reason = "Contamination report detected during routine audit by PPB."
            elif idx % 4 == 0:
                # Expired Batch!
                e_date_b = today - timedelta(days=30)
                is_recalled = False
                recall_reason = None
            elif idx % 4 == 1:
                # Expiring in 20 days (Near expiry 30 days window)
                e_date_b = today + timedelta(days=20)
                is_recalled = False
                recall_reason = None
            elif idx % 4 == 2:
                # Expiring in 50 days (Near expiry 60 days window)
                e_date_b = today + timedelta(days=50)
                is_recalled = False
                recall_reason = None
            else:
                # Expiring in 80 days (Near expiry 90 days window)
                e_date_b = today + timedelta(days=80)
                is_recalled = False
                recall_reason = None

            batch_b, _ = Batch.objects.get_or_create(
                batch_number=b_num_b,
                defaults={
                    "product": prod,
                    "manufacture_date": m_date_b,
                    "expiry_date": e_date_b,
                    "total_quantity": 300,
                    "is_recalled": is_recalled,
                    "recall_reason": recall_reason,
                    "recalled_at": timezone.now() if is_recalled else None
                }
            )
            batch_objs.append(batch_b)

        # 6. Generate Unit Codes for Batches (10 codes per batch = 300 unit codes)
        unit_code_objs = []
        for batch in batch_objs:
            for s_idx in range(1, 11):
                serial = f"SER-{batch.batch_number[-6:]}-{s_idx:04d}"
                secure_code, hmac_sig = UnitCode.generate_hmac_code(str(batch.id), serial)
                
                uc, _ = UnitCode.objects.get_or_create(
                    batch=batch,
                    serial_number=serial,
                    defaults={
                        "secure_code": secure_code,
                        "hmac_signature": hmac_sig,
                        "scan_count": 0,
                    }
                )
                unit_code_objs.append(uc)

        # 7. Seed Inventory Items into Pharmacies
        for pharmacy in pharmacy_objs:
            # Stock 10 random batches per pharmacy
            selected_batches = random.sample(batch_objs, 10)
            for batch in selected_batches:
                InventoryItem.objects.get_or_create(
                    pharmacy=pharmacy,
                    batch=batch,
                    defaults={
                        "quantity": random.randint(15, 120),
                        "purchase_price": round(random.uniform(50.0, 400.0), 2),
                        "selling_price": round(random.uniform(70.0, 550.0), 2),
                        "supplier_name": "MediPharma Kenya Distributors"
                    }
                )

        # 8. Seed Verification Scans & Clone Alerts
        # Sample genuine scans
        sample_codes = unit_code_objs[:20]
        for uc in sample_codes[:10]:
            VerificationScan.objects.create(
                unit_code=uc,
                raw_code=uc.secure_code,
                channel='WEB_QR',
                result_status='GENUINE' if not uc.batch.is_expired and not uc.batch.is_recalled else ('EXPIRED' if uc.batch.is_expired else 'RECALLED'),
                latitude=-1.286389,
                longitude=36.817223,
                ip_address='197.237.100.12',
                user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)',
                pharmacy=pharmacy_objs[0]
            )
            uc.scan_count += 1
            uc.save()

        # Seed 1 Cloned Code Attack Scenario (Scanned in Nairobi then 5 min later in Mombasa!)
        cloned_unit = sample_codes[15]
        # Scan 1: Nairobi
        VerificationScan.objects.create(
            unit_code=cloned_unit,
            raw_code=cloned_unit.secure_code,
            channel='WEB_QR',
            result_status='GENUINE',
            latitude=-1.286389,
            longitude=36.817223, # Nairobi
            ip_address='197.237.10.5',
            scanned_at=timezone.now() - timedelta(minutes=10)
        )
        # Scan 2: Mombasa (Impossible velocity!)
        VerificationScan.objects.create(
            unit_code=cloned_unit,
            raw_code=cloned_unit.secure_code,
            channel='WEB_QR',
            result_status='SUSPECTED_CLONE',
            latitude=-4.043477,
            longitude=39.668206, # Mombasa (~480km away in 5 minutes!)
            ip_address='41.203.220.88',
            scanned_at=timezone.now() - timedelta(minutes=5)
        )
        cloned_unit.scan_count = 5
        cloned_unit.is_flagged_clone = True
        cloned_unit.save()

        CloneAlert.objects.create(
            unit_code=cloned_unit,
            risk_score=95.0,
            status='PENDING',
            trigger_reasons=[
                "High Frequency: Code scanned 5 times (Threshold: 3)",
                "Velocity Anomaly: Distance 480km traveled in 5.0 mins (Speed: 5760.0 km/h > Max: 800.0 km/h)",
                "Entropy Anomaly: 3 distinct IP addresses detected within 15 minute window"
            ]
        )

        # Seed 1 Suspicious Crowd Report
        SuspiciousReport.objects.create(
            unit_code=cloned_unit,
            pharmacy=pharmacy_objs[4], # Eldoret pharmacy
            reporter_name="Juma Omondi",
            reporter_phone="+254712345678",
            product_name=cloned_unit.batch.product.brand_name,
            description="The packaging color looks faded and the batch printing has spelling errors. Medicine tastes unusual.",
            latitude=0.514277,
            longitude=35.269780,
            county="Uasin Gishu",
            status="PENDING"
        )

        call_command('seed_medicine_info', verbosity=0)
        self.stdout.write(self.style.SUCCESS("MediVerify database seeding completed successfully!"))
        self.stdout.write(self.style.SUCCESS(f"Seeded: {len(mfg_objs)} Manufacturers, {len(product_objs)} Products, {len(batch_objs)} Batches, {len(unit_code_objs)} HMAC Unit Codes, {len(pharmacy_objs)} Pharmacies."))
