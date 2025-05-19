## **Gravity List Bot**

Introducing a streamlined Discord bot designed for effortless creation and management of categorized lists across multiple channels, featuring customizable, visually enhanced text boxes.

## Getting Started

- **Environment**

1. Copy `.env.example` → `.env` and fill in your values.
2. `pip install -r requirements.txt`
3. `python bot.py`

- **Deploying**

On Railway, set the same variables under Settings → Variables, enable Persistent Volume for `lists/` (if you want data to stick), then redeploy.

- **Data Storage**

On first run, the bot creates a local file `data.json` in the project root.
– **Local dev**: this file persists across restarts but is excluded from Git.
– **Railway**: to keep data across deploys, enable a Persistent Volume or switch to a hosted database.

You can override the file path by setting `DATABASE_PATH` in your `.env`.

## Legal

- **Terms of Service:**  
  https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/TERMS.md

- **Privacy Policy:**  
  https://github.com/AZX-215/Gravity-List-Legal/blob/main/Docs/PRIVACY.md 
