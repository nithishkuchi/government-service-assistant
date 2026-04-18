**Colab Steps**
1. Upload your whole project folder zip to Colab, or mount Drive and copy the project there.
2. In Colab, install runtime packages:
```python
!pip install torch transformers sentencepiece safetensors
```
3. Change into the project folder and run:
```python
%cd /content/New_project
!python scripts/prepare_translation_layout.py
!python scripts/generate_translations.py
```
4. After it finishes, zip the translated output and download it:
```python
!zip -r translated_output.zip knowledge_base
```

**Where Files Will Be**
- `knowledge_base/<service>/translations/<language_code>/full_guide.txt`
- `knowledge_base/<service>/translations/<language_code>/faq.txt`
- `knowledge_base/<service>/translations/<language_code>/voice_points.txt`

**Supported Now**
- Scheduled: `hi bn te mr ta ur gu kn ml or pa as mai sa sat ks ne sd mni`
- Additional: `bho awa mag hne`

**Not Supported By Current Free Model**
- `gom doi brx tcy raj bgc mwr bns gon kru`

**After You Bring The Files Back**
- I will wire the app to load translated files automatically.
- Then I will fix the tab-reading bug and the FAQ-only reading bug.
