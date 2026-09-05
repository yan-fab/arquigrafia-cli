# Arquigrafia Uploader & Organizer 🚀

A modern, fast, and intelligent application to automate the upload and organization of architectural photographs to the [Arquigrafia](https://www.arquigrafia.org.br) platform.

This project features a custom visual identity in **Marsala** theme, gradient titles inspired by modern block aesthetics, and local **Artificial Intelligence (BLIP)** integration for automatic image description and tag generation.

---

## ✨ Features

- **Local Visual AI (BLIP-base):** Automatically analyzes the physical structure of the photograph and generates a complementary text description in Portuguese.
- **Controlled Architectural Vocabulary (VCAA USP):** Integrated architectural ontology and controlled terminology from FAU-USP with over 4,500 terms and automatic keyword matching.
- **Smart Geocoding (GPS + Nominatim):** Extracts latitude/longitude from EXIF metadata and retrieves the exact street name, neighborhood, city, and points of interest (POI).
- **Geolocation Auditor & Updater:** Batch audit and update missing coordinates for all cataloged profile photos using internal metadata and OpenStreetMap.
- **Automatic Collection Creation:** Auto-grouping of photos by architectural work or location, with one-click automatic collection creation directly on the platform.
- **Location-Based Naming:** Intelligently names the upload title based on the retrieved location/POI (e.g., *Sesc 24 de Maio*, *Fórum João Mendes*).
- **Smart Compression:** Automatically compresses large files to under 10 MB to ensure compliance with server limitations while preserving EXIF metadata.
- **Marsala Theme & Flow Progress:** Sleek interface featuring prompt guides and real-time upload speed (`KB/s`) estimation.
- **Flexible Source Selection:** Allows uploading an entire folder or a single image file (`.jpg`, `.jpeg`, `.png`, `.webp`).
- **Secure Session Persistence:** Stores credentials safely encrypted using the operating system's keyring (Windows Keyring).

---

## 🛠️ Installation and Usage

### Option 1: Standalone Executable (Ready to Use)
You can run the pre-compiled, independent executable directly:
1. Navigate to the `dist/` directory of the project.
2. Run the `arquigrafia.exe` file.

### Option 2: Running from Source
To run the application within your own Python environment (requires Python 3.10+):

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the application:
   ```bash
   python main.py
   ```

---

## 📝 Project Structure

```
arquigrafia/
├── cli/
│   ├── screens/         # Interface Screens (Login, Folder, Config, Organizer, Location Audit)
│   └── utils.py         # Theme setup, fonts, and console styles
├── core/
│   ├── auth.py          # Session authentication, keyring, and albums
│   ├── exif.py          # Image metadata extraction
│   ├── geo.py           # Geocoding with local cache (.geo_cache.json)
│   ├── ia.py            # Local BLIP AI integration
│   ├── location_auditor.py # Geolocation audit and batch update module
│   ├── scanner.py       # Profile scanner and album grouping
│   ├── tags.py          # VCAA USP vocabulary matcher
│   ├── uploader.py      # Upload logic and HTTP POST handler
│   └── vcaa_tags.json   # VCAA USP vocabulary database
├── main.py              # Main entry point and flow orchestrator
└── requirements.txt     # Python dependencies
```

---

## 🔒 Credentials Security
The application uses the `keyring` library to securely interface with the Windows Credential Manager, ensuring your password is encrypted by your OS. Your credentials are only sent to the official Arquigrafia platform during authentication.

---

## 📄 License
This project is open-source and licensed under the [MIT License](LICENSE).
