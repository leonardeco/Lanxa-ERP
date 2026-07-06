import { describe, it, expect } from 'vitest';
import { esc } from './htmlEscape';

describe('esc (#29 — XSS en impresión)', () => {
  it('neutraliza el markup peligroso', () => {
    expect(esc('<script>alert(1)</script>')).toBe(
      '&lt;script&gt;alert(1)&lt;/script&gt;',
    );
    expect(esc('a & b')).toBe('a &amp; b');
    expect(esc('comilla " y apóstrofo \'')).toBe('comilla &quot; y apóstrofo &#39;');
    expect(esc('"><img src=x onerror=alert(1)>')).toBe(
      '&quot;&gt;&lt;img src=x onerror=alert(1)&gt;',
    );
  });

  it('deja el texto normal intacto y trata null/undefined como cadena vacía', () => {
    expect(esc('Distribuidora El Ozono S.A.S.')).toBe('Distribuidora El Ozono S.A.S.');
    expect(esc(null)).toBe('');
    expect(esc(undefined)).toBe('');
    expect(esc(1234)).toBe('1234');
  });
});
