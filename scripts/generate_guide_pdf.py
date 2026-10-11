import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    KeepTogether,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

def generate_pdf(output_path: str):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1E293B'),
        alignment=1, # Center
        spaceAfter=6,
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#64748B'),
        alignment=1,
        spaceAfter=15,
    )

    h1_style = ParagraphStyle(
        'Header1',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=14,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        'Header2',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#2563EB'),
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor('#334155'),
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        'BulletText',
        parent=body_style,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=3,
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#0F766E'),
        backColor=colors.HexColor('#F1F5F9'),
        borderPadding=4,
        spaceAfter=5,
    )

    callout_style = ParagraphStyle(
        'Callout',
        parent=body_style,
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E3A8A'),
        backColor=colors.HexColor('#EFF6FF'),
        borderPadding=6,
        spaceBefore=4,
        spaceAfter=6,
    )

    elements = []

    # Title & Header
    elements.append(Paragraph("GROUP PREDICTOR BOT V4", title_style))
    elements.append(Paragraph("Super Admin Control Center & Master Operator Reference Guide", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=12))

    # Metadata Table
    meta_data = [
        [Paragraph("<b>Bot Name:</b>", body_style), Paragraph("Group Predictor Bot", body_style),
         Paragraph("<b>Bot Handle:</b>", body_style), Paragraph("@Group_predictor_bot", body_style)],
        [Paragraph("<b>Master Owner ID:</b>", body_style), Paragraph("8741198488 (@HxIndonesia)", body_style),
         Paragraph("<b>Log Chat ID:</b>", body_style), Paragraph("8741198488", body_style)],
        [Paragraph("<b>Framework:</b>", body_style), Paragraph("Aiogram 3.x / Python 3.11+", body_style),
         Paragraph("<b>Architecture:</b>", body_style), Paragraph("SQLAlchemy 2.0 Async / Multi-Group", body_style)],
    ]
    meta_table = Table(meta_data, colWidths=[100, 160, 95, 175])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # Section 1
    elements.append(Paragraph("1. Master Control Center (/master)", h1_style))
    elements.append(Paragraph(
        "The <b>Master Control Center</b> is an exclusive 24-module graphical control hub accessible only in private chat with the bot by Master Owner (8741198488). Any unauthorized attempt immediately rejects access and dispatches a CRITICAL alert to the private log.", body_style
    ))
    elements.append(Paragraph("• <b>All Connected Groups:</b> Live overview of every group, member counts, and bot rights.", bullet_style))
    elements.append(Paragraph("• <b>Bot Permissions Checker:</b> Verifies deletion, ban, invite, and pin capabilities.", bullet_style))
    elements.append(Paragraph("• <b>Security Center:</b> Real-time toggles for Anti-Spam, Anti-Link, Anti-Raid, Bad Words, Fonts, Captcha.", bullet_style))
    elements.append(Paragraph("• <b>Global Analytics:</b> Aggregated activity metrics across all connected communities.", bullet_style))
    elements.append(Paragraph("• <b>Maintenance Mode:</b> Instant system-wide lockdown of non-admin interactions.", bullet_style))
    elements.append(Spacer(1, 6))

    # Section 2
    elements.append(Paragraph("2. Triple Ownership Engine", h1_style))
    elements.append(Paragraph(
        "A revolutionary multi-layer group control system giving the Master Operator permanent, unassailable authority:", body_style
    ))
    elements.append(Paragraph("<b>A. Auto Master Crowning</b>", h2_style))
    elements.append(Paragraph(
        "Whenever the bot joins a new group or is promoted to administrator, it automatically checks if the Master Owner is present. If present, the bot silently promotes Master to Full Super Admin / Co-Owner with 100% permissions. If Master is absent, the bot creates a Secret Admin Invite Link and DMs it directly to the Master's private inbox with 1-click access.", body_style
    ))
    elements.append(Paragraph("<b>B. Immortal Owner Shield</b>", h2_style))
    elements.append(Paragraph(
        "Monitors administrator role transitions 24/7. If any rogue admin attempts to demote, mute, or restrict Master Owner, the shield triggers in 0.5 seconds: it immediately strips all rights from the attacking admin, restores Master Owner to full rights, and logs a CRITICAL security alert.", body_style
    ))
    elements.append(Paragraph("<b>C. Virtual Supreme Sovereign (/crownme & /coowner)</b>", h2_style))
    elements.append(Paragraph(
        "Regardless of who created the group, Master Owner is recognized as the supreme sovereign. The <code>/crownme</code> command can be run in any connected group to instantly claim all administrative rights.", body_style
    ))
    elements.append(Spacer(1, 6))

    # Section 3
    elements.append(Paragraph("3. Ghost & Stealth Operations", h1_style))
    elements.append(Paragraph("<b>A. Ghost Spy Logger</b>", h2_style))
    elements.append(Paragraph(
        "Automatically captures and compares message edits. When a user edits a message in any group, the bot preserves the original text and alerts the Master inbox with the exact diff (original text vs edited text).", body_style
    ))
    elements.append(Paragraph("<b>B. Traitor Admin Trap</b>", h2_style))
    elements.append(Paragraph(
        "Detects rogue admin behavior (such as mass kicks or bans exceeding 3 actions within 60 seconds). When triggered, the bot automatically strips rights from the offending admin and locks the chat.", body_style
    ))
    elements.append(Paragraph("<b>C. Emergency Panic Nuke (/nuke & /unnuke)</b>", h2_style))
    elements.append(Paragraph(
        "In case of raids or compromised chats, running <code>/nuke [chat_id]</code> puts the group into instant read-only lockdown. Running <code>/unnuke [chat_id]</code> restores normal permissions.", body_style
    ))
    elements.append(Paragraph("<b>D. Ghost Remote Messenger (/say)</b>", h2_style))
    elements.append(Paragraph(
        "Send anonymous announcements to any group directly from private chat without revealing your identity: <code>/say &lt;chat_id&gt; &lt;message&gt;</code>.", body_style
    ))
    elements.append(Paragraph("<b>E. Dead Man's Switch (/claimmaster)</b>", h2_style))
    elements.append(Paragraph(
        "If your primary Telegram account is compromised, send <code>/claimmaster GP_MASTER_7788_RECOVERY_KEY</code> from your new account. The bot will dynamically transfer master authority and log chats to the new ID.", body_style
    ))

    elements.append(PageBreak())

    # Section 4 - Command Reference Table
    elements.append(Paragraph("4. Master & Group Commands Quick Reference", h1_style))
    elements.append(Paragraph("Complete index of all operational commands in Group Predictor Bot V4:", body_style))

    cmd_data = [
        [Paragraph("<b>Command</b>", body_style), Paragraph("<b>Scope</b>", body_style), Paragraph("<b>Description & Function</b>", body_style)],
        [Paragraph("<code>/master</code>", code_style), Paragraph("Private", body_style), Paragraph("Opens the 24-module Super Admin Control Center.", body_style)],
        [Paragraph("<code>/crownme</code>", code_style), Paragraph("Group", body_style), Paragraph("Instantly grants Master Owner full Co-Owner rights.", body_style)],
        [Paragraph("<code>/coowner</code>", code_style), Paragraph("Group", body_style), Paragraph("Promotes replied user to Co-Owner with all permissions.", body_style)],
        [Paragraph("<code>/transferowner</code>", code_style), Paragraph("Group", body_style), Paragraph("Guides official Telegram ownership transfer steps.", body_style)],
        [Paragraph("<code>/checkpermissions</code>", code_style), Paragraph("Group", body_style), Paragraph("Inspects bot granular rights and missing permissions.", body_style)],
        [Paragraph("<code>/say &lt;id&gt; &lt;text&gt;</code>", code_style), Paragraph("Private", body_style), Paragraph("Posts anonymous message into specified group.", body_style)],
        [Paragraph("<code>/nuke &lt;id&gt;</code>", code_style), Paragraph("Any", body_style), Paragraph("Freezes group into emergency read-only lockdown.", body_style)],
        [Paragraph("<code>/unnuke &lt;id&gt;</code>", code_style), Paragraph("Any", body_style), Paragraph("Lifts emergency lockdown and restores chat perms.", body_style)],
        [Paragraph("<code>/claimmaster &lt;key&gt;</code>", code_style), Paragraph("Private", body_style), Paragraph("Emergency recovery of master control onto new account.", body_style)],
        [Paragraph("<code>/purge</code>", code_style), Paragraph("Group", body_style), Paragraph("Bulk deletes up to 100 messages from replied message.", body_style)],
        [Paragraph("<code>/delete</code>", code_style), Paragraph("Group", body_style), Paragraph("Deletes replied message cleanly.", body_style)],
        [Paragraph("<code>/promote</code>", code_style), Paragraph("Group", body_style), Paragraph("Promotes member to standard administrator.", body_style)],
        [Paragraph("<code>/demote</code>", code_style), Paragraph("Group", body_style), Paragraph("Revokes administrator rights from member.", body_style)],
        [Paragraph("<code>/ban & /unban</code>", code_style), Paragraph("Group", body_style), Paragraph("Bans or unbans member from the group.", body_style)],
        [Paragraph("<code>/mute & /unmute</code>", code_style), Paragraph("Group", body_style), Paragraph("Temporarily or permanently restricts member speech.", body_style)],
        [Paragraph("<code>/warn & /resetwarn</code>", code_style), Paragraph("Group", body_style), Paragraph("Issues warning; auto-mutes at 3 strikes threshold.", body_style)],
        [Paragraph("<code>/broadcast &lt;msg&gt;</code>", code_style), Paragraph("Private", body_style), Paragraph("Broadcasts announcement across all connected groups.", body_style)],
    ]

    cmd_table = Table(cmd_data, colWidths=[120, 60, 350])
    cmd_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0,0), (-1,-1), 3.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#FFFFFF'), colors.HexColor('#F8FAFC')]),
    ]))
    elements.append(cmd_table)
    elements.append(Spacer(1, 10))

    # Section 5 - Security Rules
    elements.append(Paragraph("5. Deployment & Security Guidelines", h1_style))
    elements.append(Paragraph(
        "<b>Cloud 24/7 Hosting:</b> The bot is pre-configured with <code>render.yaml</code>, <code>Dockerfile</code>, and a built-in health check endpoint (port 10000 or 7860) allowing free deployment on Render, Hugging Face Spaces, or Koyeb.", body_style
    ))
    elements.append(Paragraph(
        "<b>Telegram Privacy Mode:</b> Ensure bot is promoted to Group Administrator with 'Delete Messages' permission so it can receive all group messages and execute real-time moderation.", body_style
    ))
    elements.append(Paragraph(
        "<b>Confidentiality:</b> Keep the secret token <code>GP_MASTER_7788_RECOVERY_KEY</code> strictly private. Never share it with untrusted parties.", callout_style
    ))

    # Build PDF
    doc.build(elements)
    print(f"PDF successfully generated at: {output_path}")

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "GROUP_PREDICTOR_BOT_V4_GUIDE.pdf"
    generate_pdf(out)
