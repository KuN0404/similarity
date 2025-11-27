import nltk
import ssl

# Handle SSL certificate issues
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

def download_nltk_data():
    """Download all required NLTK data"""
    
    print("=" * 60)
    print("NLTK Data Setup for SISINDO")
    print("=" * 60)
    
    required_packages = [
        'punkt',           # Sentence tokenizer
        'punkt_tab',       # Additional punkt data
        'stopwords',       # Stopwords (optional)
    ]
    
    print("\nDownloading NLTK packages...\n")
    
    for package in required_packages:
        try:
            print(f"📦 Downloading '{package}'...", end=" ")
            nltk.download(package, quiet=True)
            print("✅ Done")
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ NLTK Setup Complete!")
    print("=" * 60)
    
    # Test tokenization
    print("\n🧪 Testing tokenization...")
    try:
        from nltk.tokenize import sent_tokenize
        test_text = "Ini adalah kalimat pertama. Ini adalah kalimat kedua."
        sentences = sent_tokenize(test_text)
        print(f"   Input: {test_text}")
        print(f"   Output: {sentences}")
        print("   ✅ Tokenization works!")
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        print("   Please check NLTK installation.")

if __name__ == "__main__":
    download_nltk_data()