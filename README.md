# Plotter Studio - A Web-Based Pen Plotter Control System
Your project is a modern web application for controlling pen plotters (specifically NextDraw/AxiDraw devices). It's designed to make physical art creation with pen plotters easy and accessible.

What It Does:
Manages SVG files - Upload, preview, rotate, rename, and delete SVG artwork
Controls plotting - Start/stop plotting jobs with real-time progress monitoring
Provides manual controls - Direct control over plotter motors and pen position
Estimates plotting - Shows time and distance before you commit to a plot
Configures settings - Paper sizes (A3/A4/A5/A6), speed, pen pressure

Architecture:
Backend: Python FastAPI server that communicates with the plotter hardware
Frontend: Svelte/TypeScript dashboard with real-time preview and controls
Deployment: Optimized for Raspberry Pi, runs as a systemd service
Monorepo structure with separate apps/api/ and apps/dashboard/

Target Users:
Artists, designers, and hobbyists who want a clean, modern interface for creating physical pen plotter artwork from digital SVG files.