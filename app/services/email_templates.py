from html import escape

_INTROS = {
    "REGISTRO": "Gracias por sumarte a Huellitas. Para activar tu cuenta ingresá este código:",
    "LOGIN": "Recibimos un pedido para iniciar sesión en tu cuenta. Ingresá este código para continuar:",
}


def build_code_email(nombre: str, code: str, proposito: str, minutes: int) -> dict[str, str]:
    """Correo con el código de verificación (marca Huellitas, paleta verde)."""
    intro = _INTROS.get(proposito, _INTROS["LOGIN"])
    subject = f"Tu código de verificación de Huellitas: {code}"
    text = (
        f"Hola {nombre}:\n\n{intro}\n\n{code}\n\nVence en {minutes} minutos. "
        "Si no fuiste vos, ignorá este correo.\n\nEquipo Huellitas"
    )
    html = f"""<!doctype html><html><body style="margin:0;background:#f0fdf4;font-family:Arial,sans-serif;color:#14532d">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:32px 16px">
    <table role="presentation" width="100%" style="max-width:480px;background:#ffffff;border-radius:16px;overflow:hidden">
      <tr><td style="background:#15803d;color:#ffffff;padding:20px 28px;font-size:20px;font-weight:bold">🐾 Huellitas</td></tr>
      <tr><td style="padding:28px">
        <p style="margin:0 0 12px">Hola {escape(nombre)}:</p>
        <p style="margin:0 0 20px;line-height:1.5">{intro}</p>
        <p style="margin:0 0 20px;text-align:center;font-size:34px;letter-spacing:8px;font-weight:bold;color:#15803d">{code}</p>
        <p style="margin:0;color:#4b5563;font-size:14px">Vence en {minutes} minutos. Si no fuiste vos, ignorá este correo.</p>
      </td></tr>
    </table>
  </td></tr></table></body></html>"""
    return {"subject": subject, "text": text, "html": html}
