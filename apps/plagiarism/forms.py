from django import forms
from django.core.exceptions import ValidationError
import os

class MultipleFileInput(forms.ClearableFileInput):
    """Custom widget untuk multiple file upload"""
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    """Custom field untuk multiple file upload"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class PlagiarismCheckForm(forms.Form):
    # Allowed file extensions
    ALLOWED_EXTENSIONS = ['.pdf', '.docx']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
    
    SOURCE_CHOICES = (
        ('local', 'Repository Lokal'),
        ('internet', 'Internet (Google)'),
        ('both', 'Keduanya (Lokal & Internet)'),
    )
    
    input_type = forms.ChoiceField(
        choices=(('file', 'Upload File'), ('text', 'Paste Text')),
        widget=forms.RadioSelect,
        initial='file',
        label="Metode Input",
        required=True
    )
    
    document_file = MultipleFileField(  # GANTI: MultipleFileField
        required=False,
        label="Upload Dokumen (DOCX/PDF)",
        help_text="Hanya format .docx dan .pdf. Maksimal 10MB per file.",
        widget=MultipleFileInput(attrs={
            'class': 'custom-file-input',
            'id': 'id_document_file',
            'accept': '.docx,.pdf'
        })
    )
    
    pasted_text = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 10, 
            'class': 'form-control',
            'id': 'id_pasted_text',
            'placeholder': 'Tempel teks di sini...',
            'maxlength': '50000'
        }),
        label="Tempel Teks",
        help_text="Maksimal 50.000 karakter",
        max_length=50000
    )
    
    source_mode = forms.ChoiceField(
        choices=SOURCE_CHOICES, 
        label="Sumber Pengecekan",
        initial='both',
        required=True,
        widget=forms.Select(attrs={'class': 'form-control custom-select'})
    )

    def clean_document_file(self):
        """Validasi file upload - support multiple files"""
        files = self.cleaned_data.get('document_file')
        
        if not files:
            return files
        
        # Jika single file, convert ke list
        if not isinstance(files, list):
            files = [files] if files else []
        
        validated_files = []
        
        for file in files:
            if not file:
                continue
                
            # Validasi extension
            file_ext = os.path.splitext(file.name)[1].lower()
            if file_ext not in self.ALLOWED_EXTENSIONS:
                raise ValidationError(
                    f'File "{file.name}": Format tidak didukung. Hanya {", ".join(self.ALLOWED_EXTENSIONS)} yang diizinkan.'
                )
            
            # Validasi ukuran file
            if file.size > self.MAX_FILE_SIZE:
                raise ValidationError(
                    f'File "{file.name}": Ukuran terlalu besar. Maksimal {self.MAX_FILE_SIZE / (1024*1024):.0f}MB.'
                )
            
            # Validasi MIME type (extra security)
            allowed_mimes = {
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            }
            
            if hasattr(file, 'content_type'):
                expected_mime = allowed_mimes.get(file_ext)
                if expected_mime and file.content_type not in [expected_mime, 'application/octet-stream']:
                    raise ValidationError(
                        f'File "{file.name}": Tipe file tidak sesuai.'
                    )
            
            validated_files.append(file)
        
        return validated_files if validated_files else None
    
    def clean_pasted_text(self):
        """Validasi pasted text"""
        text = self.cleaned_data.get('pasted_text', '').strip()
        
        if not text:
            return text
        
        # Validasi minimal karakter
        if len(text) < 100:
            raise ValidationError('Teks terlalu pendek. Minimal 100 karakter.')
        
        # Validasi maksimal karakter
        if len(text) > 50000:
            raise ValidationError('Teks terlalu panjang. Maksimal 50.000 karakter.')
        
        return text

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        input_type = cleaned_data.get("input_type")
        document_file = cleaned_data.get("document_file")
        pasted_text = cleaned_data.get("pasted_text")

        if input_type == 'file':
            if not document_file:
                self.add_error('document_file', "Harap upload file dokumen.")
            cleaned_data['pasted_text'] = None
            
        elif input_type == 'text':
            if not pasted_text:
                self.add_error('pasted_text', "Harap tempelkan teks yang akan diperiksa.")
            cleaned_data['document_file'] = None
        
        return cleaned_data