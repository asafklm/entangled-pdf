"""Certificate management for PdfServer.

Can be used as a library or run as a CLI script:
    python -m src.certs generate              # Generate new cert
    python -m src.certs status                  # Check cert status
    python -m src.certs generate --force        # Regenerate expired cert
    python -m src.certs generate --cert PATH --key PATH  # Use existing
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)


def get_cert_directory() -> Path:
    """Get the certificate storage directory (XDG compliant).
    
    Returns:
        Path to ~/.local/share/pdf_server/certs/
    """
    cert_dir = Path.home() / ".local/share/pdf_server/certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    return cert_dir


def get_cert_paths() -> Tuple[Path, Path]:
    """Get default certificate and key file paths.
    
    Returns:
        Tuple of (cert_path, key_path)
    """
    cert_dir = get_cert_directory()
    return (cert_dir / "server.crt", cert_dir / "server.key")


def generate_self_signed_cert(
    hostname: str,
    cert_path: Path,
    key_path: Path,
    days_valid: int = 365
) -> None:
    """Generate a self-signed SSL certificate.
    
    Args:
        hostname: Hostname for the certificate
        cert_path: Path to write certificate file
        key_path: Path to write private key file
        days_valid: Number of days certificate is valid
        
    Raises:
        ImportError: If cryptography library is not installed
        RuntimeError: If certificate generation fails
    """
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
    except ImportError:
        raise ImportError(
            "cryptography library not installed. "
            "Install with: pip install cryptography"
        )
    
    try:
        # Generate private key
        logger.info("Generating RSA private key...")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        logger.info(f"Generating certificate for hostname: {hostname}")
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "Local"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "Local"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PdfServer"),
            x509.NameAttribute(NameOID.COMMON_NAME, hostname),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now(timezone.utc)
        ).not_valid_after(
            datetime.now(timezone.utc) + timedelta(days=days_valid)
        ).add_extension(
            x509.SubjectAlternativeName([x509.DNSName(hostname)]),
            critical=False,
        ).sign(key, hashes.SHA256())
        
        # Write files
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(key_path, "wb") as f:
            f.write(key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        logger.info(f"Certificate saved to: {cert_path}")
        logger.info(f"Private key saved to: {key_path}")
        
    except Exception as e:
        raise RuntimeError(f"Failed to generate certificate: {e}")


def validate_certificate(cert_path: Path) -> dict:
    """Validate certificate and return information.
    
    Args:
        cert_path: Path to certificate file
        
    Returns:
        Dictionary with certificate info:
        - exists: bool
        - valid: bool
        - expired: bool
        - expires_at: datetime or None
        - hostname: str or None
        - error: str or None
    """
    result = {
        "exists": False,
        "valid": False,
        "expired": False,
        "expires_at": None,
        "hostname": None,
        "error": None
    }
    
    if not cert_path.exists():
        result["error"] = f"Certificate not found: {cert_path}"
        return result
    
    result["exists"] = True
    
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
    except ImportError:
        result["error"] = "cryptography library not installed"
        return result
    
    try:
        with open(cert_path, "rb") as f:
            cert = x509.load_pem_x509_certificate(f.read())
        
        # Check expiration
        now = datetime.now(timezone.utc)
        expires_at = cert.not_valid_after_utc
        result["expires_at"] = expires_at
        result["expired"] = now > expires_at
        
        # Get hostname from CN or SAN
        for attr in cert.subject:
            if attr.oid == NameOID.COMMON_NAME:
                result["hostname"] = attr.value
                break
        
        result["valid"] = not result["expired"]
        
        if result["expired"]:
            result["error"] = f"Certificate expired on {expires_at}"
            
    except Exception as e:
        result["error"] = f"Failed to parse certificate: {e}"
    
    return result


def copy_existing_cert(cert_path: Path, key_path: Path) -> None:
    """Copy existing certificates to the standard location.
    
    Args:
        cert_path: Source certificate file
        key_path: Source private key file
        
    Raises:
        FileNotFoundError: If source files don't exist
        RuntimeError: If copy fails
    """
    if not cert_path.exists():
        raise FileNotFoundError(f"Certificate not found: {cert_path}")
    if not key_path.exists():
        raise FileNotFoundError(f"Private key not found: {key_path}")
    
    dest_cert, dest_key = get_cert_paths()
    cert_dir = get_cert_directory()
    cert_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        import shutil
        shutil.copy2(cert_path, dest_cert)
        shutil.copy2(key_path, dest_key)
        logger.info(f"Certificate copied to: {dest_cert}")
        logger.info(f"Private key copied to: {dest_key}")
    except Exception as e:
        raise RuntimeError(f"Failed to copy certificates: {e}")


def cmd_generate(args: argparse.Namespace) -> int:
    """Handle 'generate' subcommand.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    cert_path, key_path = get_cert_paths()
    
    # Check if certificates already exist
    if cert_path.exists() and not args.force:
        info = validate_certificate(cert_path)
        if info["valid"]:
            logger.info("Valid certificates already exist.")
            logger.info(f"  Certificate: {cert_path}")
            logger.info(f"  Expires: {info['expires_at']}")
            logger.info(f"  Hostname: {info['hostname']}")
            logger.info("\nUse --force to regenerate.")
            return 0
        elif info["expired"]:
            logger.warning(f"Certificate expired on {info['expires_at']}")
            logger.info("Regenerating...")
        else:
            logger.error(f"Certificate issue: {info['error']}")
            if not args.force:
                logger.info("Use --force to overwrite.")
                return 1
    
    # Use existing certificates if provided
    if args.cert and args.key:
        try:
            copy_existing_cert(args.cert, args.key)
            logger.info("\nCustom certificates installed successfully!")
            return 0
        except Exception as e:
            logger.error(f"Failed to install certificates: {e}")
            return 1
    
    # Generate new self-signed certificate
    try:
        generate_self_signed_cert(
            hostname=args.hostname,
            cert_path=cert_path,
            key_path=key_path,
            days_valid=args.days
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("Certificate generation complete!")
        logger.info("=" * 60)
        logger.info(f"\nHostname: {args.hostname}")
        logger.info(f"Valid for: {args.days} days")
        logger.info(f"\nCertificate: {cert_path}")
        logger.info(f"Private key: {key_path}")
        logger.info("\nFirst-time browser access:")
        logger.info("You'll see a certificate warning - click 'Advanced' → 'Accept'")
        logger.info("\nTo use PdfServer:")
        logger.info("  python main.py document.pdf")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate certificate: {e}")
        return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Handle 'status' subcommand.
    
    Args:
        args: Parsed command line arguments
        
    Returns:
        Exit code (0 for valid, 1 for invalid/missing)
    """
    cert_path, key_path = get_cert_paths()
    
    logger.info("Certificate Status")
    logger.info("=" * 60)
    logger.info(f"\nCertificate directory: {cert_path.parent}")
    logger.info(f"Certificate file: {cert_path}")
    logger.info(f"Private key file: {key_path}")
    
    info = validate_certificate(cert_path)
    
    if not info["exists"]:
        logger.info("\nStatus: NOT FOUND")
        logger.info("\nTo generate certificates:")
        logger.info("  python -m src.certs generate")
        return 1
    
    logger.info(f"\nStatus: {'VALID' if info['valid'] else 'INVALID'}")
    logger.info(f"Hostname: {info['hostname']}")
    logger.info(f"Expires: {info['expires_at']}")
    
    if info["expired"]:
        logger.info("\n⚠️  Certificate has EXPIRED")
        logger.info("To regenerate:")
        logger.info("  python -m src.certs generate --force")
        return 1
    elif info["error"]:
        logger.info(f"\n⚠️  Issue: {info['error']}")
        return 1
    
    logger.info("\n✓ Certificates are ready to use")
    return 0


def main() -> int:
    """CLI entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s"
    )
    
    parser = argparse.ArgumentParser(
        description="PdfServer certificate management",
        prog="python -m src.certs"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # generate subcommand
    gen_parser = subparsers.add_parser("generate", help="Generate or install SSL certificates")
    gen_parser.add_argument(
        "--hostname",
        default="pdfserver.local",
        help="Hostname for generated certificate (default: pdfserver.local)"
    )
    gen_parser.add_argument(
        "--cert",
        type=Path,
        help="Path to existing certificate file to use"
    )
    gen_parser.add_argument(
        "--key",
        type=Path,
        help="Path to existing private key file to use"
    )
    gen_parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="Number of days certificate is valid (default: 365)"
    )
    gen_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing certificates"
    )
    
    # status subcommand
    subparsers.add_parser("status", help="Check certificate status")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "status":
        return cmd_status(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
