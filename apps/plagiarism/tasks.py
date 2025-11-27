import threading
import os
import uuid
from django.conf import settings
from django.utils import timezone
from apps.history.models import PlagiarismHistory
from .services import PlagiarismService

class PlagiarismTask:
    
    @staticmethod
    def process_document(history_id, file_path, source_mode):
        thread = threading.Thread(
            target=PlagiarismTask._process_worker,
            args=(history_id, file_path, source_mode),
            daemon=True
        )
        thread.start()
        return thread
    
    @staticmethod
    def _process_worker(history_id, file_path, source_mode):
        history = None
        try:
            history = PlagiarismHistory.objects.get(id=history_id)
            history.status = 'processing'
            history.started_at = timezone.now()
            history.progress = 0
            history.save()
            
            print(f"\n{'='*60}")
            print(f"🔍 Starting plagiarism check: {history.filename}")
            print(f"   File: {file_path}")
            print(f"   Source mode: {source_mode}")
            print(f"{'='*60}\n")
            
            service = PlagiarismService()
            
            # Step 1: Extract text
            print("📄 Step 1: Extracting text from document...")
            file_ext = os.path.splitext(file_path)[1].lower()
            
            try:
                raw_text = service.extract_text(file_path, file_ext)
            except ValueError as ve:
                # User-friendly error messages
                raise ValueError(str(ve))
            except Exception as e:
                raise ValueError(f"Gagal membaca file: {str(e)}")
            
            if not raw_text or not raw_text.strip():
                raise ValueError("Tidak dapat mengekstrak teks dari dokumen. File mungkin kosong atau rusak.")
            
            print(f"✅ Text extracted: {len(raw_text)} characters")
            
            history.progress = 10
            history.save()
            
            # Step 2: Tokenize
            print("\n🔤 Step 2: Tokenizing sentences...")
            try:
                sentences = service.tokenize(raw_text)
            except Exception as e:
                raise ValueError(f"Gagal memproses teks: {str(e)}")
            
            total_sentences = len(sentences)
            
            if total_sentences == 0:
                raise ValueError(
                    "Tidak ada kalimat valid yang dapat diperiksa. "
                    "Pastikan dokumen mengandung teks yang cukup (minimal 100 karakter)."
                )
            
            print(f"✅ Found {total_sentences} valid sentences")
            
            history.progress = 20
            history.save()
            
            # Step 3: Check plagiarism
            print(f"\n🔍 Step 3: Checking plagiarism ({source_mode} mode)...")
            print(f"   Threshold: {service.threshold}%")
            
            try:
                check_results = service.process_check(raw_text, source_mode)
            except Exception as e:
                raise ValueError(f"Error saat pemeriksaan plagiarisme: {str(e)}")
            
            plagiarized_count = len(check_results['results'])
            print(f"✅ Check completed:")
            print(f"   - Plagiarized sentences: {plagiarized_count}/{total_sentences}")
            print(f"   - Global similarity: {check_results['similarity_global']}%")
            print(f"   - Local similarity: {check_results['similarity_local']}%")
            print(f"   - Internet similarity: {check_results['similarity_internet']}%")
            
            history.progress = 80
            history.save()
            
            # Step 4: Generate report
            print("\n📊 Step 4: Generating PDF report...")
            reports_dir = os.path.join(settings.MEDIA_ROOT, 'reports')
            os.makedirs(reports_dir, exist_ok=True)
            
            report_filename = f"Report_{uuid.uuid4()}.pdf"
            report_path = os.path.join(reports_dir, report_filename)
            
            try:
                final_report = service.generate_pdf_report(
                    raw_text,
                    check_results,
                    report_path,
                    history.filename
                )
            except Exception as e:
                raise ValueError(f"Gagal membuat laporan PDF: {str(e)}")
            
            if final_report is None:
                raise ValueError("Gagal membuat laporan PDF. Silakan coba lagi.")
            
            print(f"✅ PDF report created: {report_filename}")
            
            history.progress = 95
            history.save()
            
            # Step 5: Save results
            print("\n💾 Step 5: Saving results...")
            history.similarity_score = check_results['similarity_global']
            history.similarity_local = check_results['similarity_local']
            history.similarity_internet = check_results['similarity_internet']
            
            # Save matched sources as JSON string (TextField compatible)
            import json
            matched_sources = {
                'local': check_results['local_sources'],
                'internet': check_results['internet_sources']
            }
            history.matched_sources = json.dumps(matched_sources, ensure_ascii=False)
            
            history.report_file = f"reports/{report_filename}"
            history.status = 'completed'
            history.progress = 100
            history.completed_at = timezone.now()
            history.save()
            
            # Cleanup temp file
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"🗑️  Temp file removed: {file_path}")
            
            print(f"\n{'='*60}")
            print(f"✅ COMPLETED: {history.filename}")
            print(f"   Similarity: {history.similarity_score}%")
            print(f"   Duration: {(history.completed_at - history.started_at).total_seconds():.1f}s")
            print(f"{'='*60}\n")
            
        except ValueError as ve:
            # User-friendly errors (already formatted)
            error_msg = str(ve)
            print(f"\n❌ USER ERROR: {error_msg}\n")
            
            if history:
                history.status = 'failed'
                history.error_message = error_msg
                history.completed_at = timezone.now()
                history.save()
            
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                
        except Exception as e:
            # System errors
            error_msg = f"Terjadi kesalahan sistem: {str(e)}"
            print(f"\n❌ SYSTEM ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            print()
            
            if history:
                history.status = 'failed'
                history.error_message = error_msg
                history.completed_at = timezone.now()
                history.save()
            
            if file_path and os.path.exists(file_path):
                os.remove(file_path)