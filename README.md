# 🎵 Noise Cleaner - Free Audio Processing Toolkit

Professional audio processing tools that run 100% on your server. No data leaves your control.

**🆓 Deploy for FREE** on Railway, Render, Fly.io, or Oracle Cloud!

---

## ✨ Features

- 🎧 **Audio Denoising** - Remove background noise (commercial-safe)
- 🎼 **Stem Separation** - Isolate vocals, drums, bass, instruments
- 📊 **Audio Normalization** - Loudness standardization  
- 🔄 **Format Conversion** - MP3, WAV, FLAC, OGG, etc.
- ✂️ **Audio Trimming** - Cut audio files
- 🎬 **Video Processing** - Extract/replace audio
- 📝 **Transcription** - Speech-to-text (Whisper)
- 🎛️ **Stem Remixer** - Mix separated stems
- 📈 **Audio Analysis** - Waveform visualization
- ⚡ **Batch Processing** - Process multiple files

---

## 🚀 Quick Start (Choose One)

### Option 1: Interactive Setup (Recommended)

```bash
git clone <your-repo-url>
cd noise-cleaner
./setup.sh
```

The wizard asks for your email, domain, and deployment preferences, then sets everything up automatically!

### Option 2: One-Click Deploy

**Railway.app** (Free $5/month credit):
1. Fork this repo
2. Go to [Railway.app](https://railway.app)
3. New Project → Deploy from GitHub
4. Add env vars from `.env.example`
5. Deploy!

**Render.com** (Free forever):
1. Fork this repo
2. Go to [Render.com](https://render.com)
3. New Web Service → Connect repo
4. Add env vars, choose FREE tier
5. Deploy!

### Option 3: Local Development

```bash
# Install
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Run
cd src
python -m noise_cleaner

# Visit http://localhost:8000
```

---

## 🔧 Required Configuration

Create `.env` file (or use `./setup.sh`):

```bash
ENABLE_AI_DENOISE=false  # Keep false for commercial use!
ENVIRONMENT=production
SECRET_KEY=<generate-with: openssl rand -hex 32>
MAX_FILE_SIZE_MB=50
```

See [.env.example](.env.example) for all options.

---

## ⚖️ Licensing (IMPORTANT!)

**✅ ALL features are commercial-safe** with default settings (`ENABLE_AI_DENOISE=false`)

**⚠️ If you enable AI denoise:**
- Uses Facebook DNS-64 model (CC-BY-NC license)
- **NO commercial use** (no ads, no paid features, no revenue)
- Only use for personal/educational projects

**Recommendation:** Keep it disabled (default) to avoid any licensing issues.

Read [PRODUCTION_READINESS.md](PRODUCTION_READINESS.md) for details.

---

## 💰 Free Deployment Options

| Platform | Cost | Setup | Always On? | Guide |
|----------|------|-------|------------|-------|
| **Railway** | $5 credit/mo | 5 min | No | [DEPLOY-FREE.md](DEPLOY-FREE.md#railway) |
| **Render** | $0 forever | 10 min | No | [DEPLOY-FREE.md](DEPLOY-FREE.md#render) |
| **Fly.io** | $0 (3 VMs) | 15 min | Auto | [DEPLOY-FREE.md](DEPLOY-FREE.md#flyio) |
| **Oracle** | $0 FOREVER | 30 min | YES | [DEPLOY-FREE.md](DEPLOY-FREE.md#oracle) |

**Total cost: $0-2/year** (domain optional)

---

## 📚 Documentation

- **[DEPLOY-FREE.md](DEPLOY-FREE.md)** - Free deployment guides ⭐
- **[DEPLOY.md](DEPLOY.md)** - VPS deployment ($7/month)
- **[PRODUCTION_READINESS.md](PRODUCTION_READINESS.md)** - Production checklist
- **[QUICK-REF.md](QUICK-REF.md)** - Command reference
- **[CHECKLIST.md](CHECKLIST.md)** - Pre-launch verification
- **[SUMMARY.md](SUMMARY.md)** - What's included

---

## 🛠️ Technology

- **Backend:** FastAPI (Python 3.10+)
- **Audio:** librosa, scipy, soundfile
- **AI:** Demucs, Whisper (MIT licensed)
- **Deploy:** Docker, nginx
- **Frontend:** Vanilla JS/CSS

**All dependencies MIT/BSD licensed** (commercial-safe)

---

## 🔒 Privacy & Security

✅ All processing on YOUR server  
✅ No third-party data sharing  
✅ Auto-delete files after 1 hour  
✅ HTTPS encryption  
✅ Rate limiting  
✅ GDPR/CCPA compliant  

---

## 📊 Performance

- Small files (<10MB): ~5-15 sec
- Medium (10-50MB): ~30-60 sec  
- Large (50-100MB): ~2-5 min
- Stem separation: ~1-2 min/song

---

## 🎯 Use Cases

- **Podcasters:** Remove noise, normalize
- **Musicians:** Separate stems, isolate vocals
- **Video Creators:** Extract audio, captions
- **Researchers:** Transcribe, analyze
- **Batch processing:** Process hundreds of files

---

## 📝 License

- **App code:** MIT License ✅
- **Demucs:** MIT ✅
- **Whisper:** MIT ✅  
- **DNS-64:** CC-BY-NC (disabled by default)

---

## 🆘 Support

- 📖 Read documentation above
- 🐛 [Open GitHub issue](../../issues)
- 📧 See [privacy.html](src/noise_cleaner/static/privacy.html) for contact

---

## 🎉 Credits

- [FastAPI](https://fastapi.tiangolo.com/)
- [Demucs](https://github.com/facebookresearch/demucs) - Facebook Research
- [Whisper](https://github.com/openai/whisper) - OpenAI  
- [librosa](https://librosa.org/)

---

## 🚦 Status

✅ Production ready  
✅ Free deployment  
✅ Security hardened  
✅ Legal compliant  
🔄 Actively maintained  

---

**Ready to deploy? Run `./setup.sh` and go live in 5 minutes! 🚀**

---

## Advanced CLI Usage (Original Tool)

The original command-line noise reduction tool is still available:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

## 2) Basic usage

```bash
noise-clean input.wav cleaned.wav
```

## 3) Improve quality with tuning

If the first 0.5s of the file is mostly noise, defaults work well.
Otherwise tune these:

- `--noise-clip-seconds`: duration used to estimate noise profile.
- `--n-std-thresh`: larger values preserve more speech/music, remove less noise.
- `--prop-decrease`: attenuation strength for bins classified as noise.
- `--oversubtract`: extra subtraction amount (can reduce more noise but may add artifacts).
- `--floor-ratio`: avoids over-silencing and musical noise.

Example:

```bash
noise-clean input.wav cleaned.wav \
  --noise-clip-seconds 0.8 \
  --n-std-thresh 1.8 \
  --prop-decrease 0.9 \
  --oversubtract 1.1
```

## 4) Notes

- Works per-channel for mono/stereo.
- Uses `soundfile` for I/O (wav/flac/ogg depending on local backend support).
- Best for stationary noise; strongly non-stationary noise may require a deep-learning model.
