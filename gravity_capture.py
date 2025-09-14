# commands/gravity_capture.py
# Slash commands to fetch the latest Gravity Capture release from GitHub.
# Requires: discord.py >= 2.3 (pip install -U discord.py) and aiohttp

from __future__ import annotations

import os
import asyncio
from typing import Optional, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands
import aiohttp


GC_REPO_OWNER = os.getenv("GC_REPO_OWNER", "AZX-215")
GC_REPO_NAME = os.getenv("GC_REPO_NAME", "GravityCapture")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")  # optional, raises rate limits

GITHUB_API = "https://api.github.com"
LATEST_URL = f"{GITHUB_API}/repos/{GC_REPO_OWNER}/{GC_REPO_NAME}/releases/latest"


class GravityCapture(commands.Cog):
    """Commands for distributing Gravity Capture builds."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # -------- helpers -------- #

    async def _fetch_latest_release(self) -> Dict[str, Any]:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "GravityListBot",
        }
        if GITHUB_TOKEN:
            headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

        timeout = aiohttp.ClientTimeout(total=20)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as sess:
            async with sess.get(LATEST_URL) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(
                        f"GitHub API error {resp.status}: {text[:300]}"
                    )
                return await resp.json()

    @staticmethod
    def _find_assets(release_json: Dict[str, Any]) -> Dict[str, str]:
        """Return {'exe': url, 'zip': url} if present."""
        exe_url: Optional[str] = None
        zip_url: Optional[str] = None

        for a in release_json.get("assets", []):
            name = (a.get("name") or "").lower()
            url = a.get("browser_download_url")
            if not url:
                continue
            if name.endswith(".exe") and "setup" in name:
                exe_url = url
            elif name.endswith(".zip") and "portable" in name:
                zip_url = url

        return {"exe": exe_url or "", "zip": zip_url or ""}

    # -------- slash commands -------- #

    @app_commands.command(
        name="download_grav_capture",
        description="Get the latest Gravity Capture download (Installer & Portable).",
    )
    async def download_grav_capture(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=False)
        try:
            rel = await self._fetch_latest_release()
            tag = rel.get("tag_name", "unknown")
            assets = self._find_assets(rel)

            if not assets["exe"] and not assets["zip"]:
                raise RuntimeError(
                    "No release assets were found on the latest GitHub release."
                )

            view = discord.ui.View()
            if assets["exe"]:
                view.add_item(
                    discord.ui.Button(
                        label="Installer (.exe)",
                        url=assets["exe"],
                        style=discord.ButtonStyle.link,
                    )
                )
            if assets["zip"]:
                view.add_item(
                    discord.ui.Button(
                        label="Portable (.zip)",
                        url=assets["zip"],
                        style=discord.ButtonStyle.link,
                    )
                )

            embed = discord.Embed(
                title="Gravity Capture — Latest Release",
                description=f"Tag: **{tag}**\nRepo: `{GC_REPO_OWNER}/{GC_REPO_NAME}`",
                color=0x5865F2,
            )
            embed.set_footer(text="Downloads are served from GitHub Releases")

            await interaction.followup.send(embed=embed, view=view)

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Sorry, I couldn’t fetch the latest release "
                f"for `{GC_REPO_OWNER}/{GC_REPO_NAME}`.\n`{e}`",
                ephemeral=True,
            )

    @app_commands.command(
        name="grav_capture_version",
        description="Show latest Gravity Capture version + SHA256 checksums.",
    )
    async def grav_capture_version(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            rel = await self._fetch_latest_release()
            tag = rel.get("tag_name", "unknown")
            assets = rel.get("assets", [])

            # collect checksums from .sha256 files if present
            lines = []
            for a in assets:
                name = a.get("name", "")
                url = a.get("browser_download_url", "")
                if name.endswith(".sha256"):
                    lines.append(f"- `{name}` → {url}")

            if not lines:
                lines.append("_No checksum files were attached to the release._")

            embed = discord.Embed(
                title="Gravity Capture — Latest Version",
                description=f"Tag: **{tag}**",
                color=0x57F287,
            )
            embed.add_field(name="Checksums", value="\n".join(lines), inline=False)
            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                f"⚠️ Couldn’t get the latest version info: `{e}`", ephemeral=True
            )


async def setup(bot: commands.Bot):
    """discord.py extension entrypoint."""
    await bot.add_cog(GravityCapture(bot))
