/*!
 * vol_formula_engine.js
 * Lightweight, safe, Excel-style formula evaluator for the Volume Pekerjaan page.
 *
 * Supported:
 *  - Literals: numbers (accept id-ID style: 1.000,25, also 1_000.25), parentheses ( )
 *  - Variables: identifiers [A-Za-z_][A-Za-z0-9_]* (resolved from `variables` object)
 *  - Operators: +  -  *  /  ^   (power)
 *  - Functions (case-insensitive): MIN, MAX, SUM, AVG, ABS, ROUND(x[, n]), CEIL, FLOOR, POW(a,b)
 *  - Argument separator: comma ","  (e.g., min(1, 2, 3))
 *
 * Notes:
 *  - Expression may start with "=" (optional). Example: "= panjang * lebar * 0,2".
 *  - Decimal comma is supported inside numbers; thousands "." will be stripped automatically
 *    when a comma is present. Examples recognized as the same number:
 *      "1.000,25"  =>  1000.25
 *      "1,000.25"  =>  1000.25
 *      "1000,25"   =>  1000.25
 *      "1_000.25"  =>  1000.25
 *  - Unary minus/plus are supported by rewriting "-x" as "0 - x" (Excel-like precedence).
 *  - No eval(), no access to window/global scope.
 */

(function () {
  const G = (typeof window !== 'undefined') ? window : globalThis;
  if (G.VolFormula && typeof G.VolFormula.evaluate === 'function') {
    // already loaded
    return;
  }

  // -------- number helpers (locale aware parsing: id-ID & en-US mixed) --------
  function normalizeNumberToken(raw, nextChAfterToken) {
    // remove spaces & underscores first
    let s = raw.replace(/\s+/g, '').replace(/_/g, '');
    const hasComma = s.indexOf(',') !== -1;
    const hasDot = s.indexOf('.') !== -1;

    // If token ends with a comma used as function separator, don't include it as decimal.
    // Our tokenizer ensures commas belong to numbers only when followed immediately by a digit.
    // So nothing else to do here with nextChAfterToken.

    if (hasComma && hasDot) {
      // Assume "." thousands, "," decimal  -> strip "." and replace "," with "."
      s = s.replace(/\./g, '').replace(',', '.');
    } else if (hasComma) {
      // Only comma present -> treat as decimal
      s = s.replace(',', '.');
    }
    return s;
  }

  function toNumberStrict(str) {
    const n = Number(str);
    if (!Number.isFinite(n)) {
      throw new Error('Angka tidak valid');
    }
    return n;
  }

  // -------- tokenizer --------
  const TT = {
    NUM: 'num',
    ID: 'id',
    OP: 'op',
    LP: 'lp',
    RP: 'rp',
    COMMA: 'comma',
    FUNC: 'func'
  };

  function isIdentStart(ch) { return /[A-Za-z_]/.test(ch); }
  function isIdentPart(ch)  { return /[A-Za-z0-9_]/.test(ch); }
  function isDigit(ch)      { return /[0-9]/.test(ch); }

  function tokenize(expr) {
    const src = String(expr || '').trim();
    const s = src[0] === '=' ? src.slice(1) : src; // strip leading "=" (optional)
    const tokens = [];
    let i = 0;
    let prevType = null; // for unary +/- detection

    while (i < s.length) {
      const ch = s[i];

      // whitespace -> skip
      if (/\s/.test(ch)) { i++; continue; }

      // number literal (id-ID aware)
      if (isDigit(ch) || (ch === '.' && isDigit(s[i+1])) || (ch === ',' && isDigit(s[i+1]))) {
        let j = i;
        // Consume characters that can be part of a localized number
        // Allow '.' or ',' only if followed by a digit (so "1, 2" won't pull comma)
        while (j < s.length) {
          const c = s[j];
          const next = s[j+1];
          if (isDigit(c) || c === '_' ||
              (c === '.' && isDigit(next)) ||
              (c === ',' && isDigit(next))) {
            j++;
          } else {
            break;
          }
        }
        const rawNum = s.slice(i, j);
        const norm = normalizeNumberToken(rawNum, s[j]);
        tokens.push({ type: TT.NUM, value: norm });
        prevType = TT.NUM;
        i = j;
        continue;
      }

      // identifier / function
      if (isIdentStart(ch)) {
        let j = i + 1;
        while (j < s.length && isIdentPart(s[j])) j++;
        const name = s.slice(i, j);
        // function if next non-space char is "("
        let k = j;
        while (k < s.length && /\s/.test(s[k])) k++;
        if (s[k] === '(') {
          tokens.push({ type: TT.FUNC, value: name });
          prevType = TT.FUNC;
          i = j;
          continue;
        } else {
          tokens.push({ type: TT.ID, value: name });
          prevType = TT.ID;
          i = j;
          continue;
        }
      }

      // parentheses
      if (ch === '(') { tokens.push({ type: TT.LP, value: ch }); prevType = TT.LP; i++; continue; }
      if (ch === ')') { tokens.push({ type: TT.RP, value: ch }); prevType = TT.RP; i++; continue; }

      // comma (argument separator)
      if (ch === ',') { tokens.push({ type: TT.COMMA, value: ch }); prevType = TT.COMMA; i++; continue; }

      // operators
      if ('+-*/^'.indexOf(ch) !== -1) {
        // handle unary +/-
        const isUnaryContext = (prevType === null || prevType === TT.OP || prevType === TT.LP || prevType === TT.COMMA || prevType === TT.FUNC);
        if (isUnaryContext && (ch === '+' || ch === '-')) {
          // Treat unary "+" as no-op, unary "-" as "0 -"
          if (ch === '+') {
            // skip unary plus
            i++;
            continue;
          } else {
            // inject 0 then binary '-'
            tokens.push({ type: TT.NUM, value: '0' });
            tokens.push({ type: TT.OP, value: '-' });
            prevType = TT.OP;
            i++;
            continue;
          }
        }
        tokens.push({ type: TT.OP, value: ch });
        prevType = TT.OP;
        i++;
        continue;
      }

      // unknown
      const snippet = s.slice(Math.max(0, i-5), Math.min(s.length, i+5));
      throw new Error(`Token tidak dikenal di posisi ${i+1}: "${snippet}"`);
    }
    return tokens;
  }

  // -------- shunting-yard: to RPN --------
  const precedence = { '^': 4, '*': 3, '/': 3, '+': 2, '-': 2 };
  const rightAssoc = { '^': true };

  function toRpn(tokens) {
    const output = [];
    const ops = [];
    // Track function arg counts: push null for plain "(", or an integer for function call.
    const argCountStack = [];

    for (let i = 0; i < tokens.length; i++) {
      const t = tokens[i];

      if (t.type === TT.NUM || t.type === TT.ID) {
        output.push(t);
        continue;
      }

      if (t.type === TT.FUNC) {
        // function token goes to operator stack; its "(" will follow
        ops.push(t);
        continue;
      }

      if (t.type === TT.COMMA) {
        // pop until '('
        while (ops.length && ops[ops.length - 1].type !== TT.LP) {
          output.push(ops.pop());
        }
        if (!ops.length) throw new Error('Koma di luar pemanggilan fungsi');
        // Increment arg count for current function
        if (!argCountStack.length || argCountStack[argCountStack.length - 1] == null) {
          throw new Error('Koma tidak berada dalam argumen fungsi');
        }
        argCountStack[argCountStack.length - 1]++;
        continue;
      }

      if (t.type === TT.OP) {
        const o1 = t.value;
        while (ops.length) {
          const top = ops[ops.length - 1];
          if (top.type === TT.OP) {
            const o2 = top.value;
            const cond = (rightAssoc[o1])
              ? (precedence[o1] < precedence[o2])
              : (precedence[o1] <= precedence[o2]);
            if (cond) {
              output.push(ops.pop());
              continue;
            }
          } else if (top.type === TT.FUNC) {
            // functions on stack have higher precedence than any operator until '('
            output.push(ops.pop());
            continue;
          }
          break;
        }
        ops.push(t);
        continue;
      }

      if (t.type === TT.LP) {
        ops.push(t);
        // if top of ops (below the '(') is a function, we start counting its args
        const prev = ops[ops.length - 2];
        if (prev && prev.type === TT.FUNC) {
          argCountStack.push(1); // first argument started
        } else {
          argCountStack.push(null); // plain parenthesis
        }
        continue;
      }

      if (t.type === TT.RP) {
        // pop until '('
        while (ops.length && ops[ops.length - 1].type !== TT.LP) {
          output.push(ops.pop());
        }
        if (!ops.length) throw new Error('Kurung tutup tidak seimbang');
        // pop '('
        ops.pop();
        const argc = argCountStack.pop();

        // if previous is function, pop it to output with arg count
        if (ops.length && ops[ops.length - 1].type === TT.FUNC) {
          const fn = ops.pop();
          output.push({ type: 'call', name: fn.value, argc: argc || 0 });
        }
        continue;
      }

      throw new Error('Token tidak didukung');
    }

    // drain ops
    while (ops.length) {
      const t = ops.pop();
      if (t.type === TT.LP || t.type === TT.RP) throw new Error('Kurung tidak seimbang');
      if (t.type === TT.FUNC) throw new Error('Pemanggilan fungsi tanpa kurung tutup');
      output.push(t);
    }

    return output;
  }

  // -------- evaluation --------
  const fnImpl = {
    min: (...xs) => {
      if (xs.length < 1) throw new Error('MIN membutuhkan ≥1 argumen');
      return xs.reduce((a, b) => Math.min(a, b));
    },
    max: (...xs) => {
      if (xs.length < 1) throw new Error('MAX membutuhkan ≥1 argumen');
      return xs.reduce((a, b) => Math.max(a, b));
    },
    sum: (...xs) => xs.reduce((a, b) => a + b, 0),
    avg: (...xs) => {
      if (xs.length < 1) throw new Error('AVG membutuhkan ≥1 argumen');
      return xs.reduce((a, b) => a + b, 0) / xs.length;
    },
    abs: (x) => Math.abs(x),
    round: (x, n = 0) => {
      n = Number(n|0);
      const f = Math.pow(10, n);
      // HALF_UP
      return x >= 0 ? Math.floor(x * f + 0.5) / f : Math.ceil(x * f - 0.5) / f;
    },
    ceil: (x) => Math.ceil(x),
    floor: (x) => Math.floor(x),
    pow: (a, b) => Math.pow(a, b)
  };

  const consts = {
    pi: Math.PI,
    e: Math.E
  };

  function evalRpn(rpn, variables) {
    const st = [];
    for (let i = 0; i < rpn.length; i++) {
      const t = rpn[i];
      if (t.type === TT.NUM) {
        st.push(toNumberStrict(t.value));
        continue;
      }
      if (t.type === TT.ID) {
        const name = t.value;
        if (Object.prototype.hasOwnProperty.call(variables, name)) {
          const v = variables[name];
          const num = Number(v);
          if (!Number.isFinite(num)) throw new Error(`Variabel "${name}" bukan angka`);
          st.push(num);
        } else if (Object.prototype.hasOwnProperty.call(consts, name.toLowerCase())) {
          st.push(consts[name.toLowerCase()]);
        } else {
          throw new Error(`Variabel tidak dikenal: ${name}`);
        }
        continue;
      }
      if (t.type === TT.OP) {
        const b = st.pop(); const a = st.pop();
        if (a === undefined || b === undefined) throw new Error('Operator kekurangan operand');
        switch (t.value) {
          case '+': st.push(a + b); break;
          case '-': st.push(a - b); break;
          case '*': st.push(a * b); break;
          case '/':
            if (b === 0) throw new Error('Pembagian dengan nol');
            st.push(a / b);
            break;
          case '^': st.push(Math.pow(a, b)); break;
          default: throw new Error('Operator tidak didukung');
        }
        continue;
      }
      if (t.type === 'call') {
        const name = String(t.name || '').toLowerCase();
        const argc = t.argc|0;
        const impl = fnImpl[name];
        if (!impl) throw new Error(`Fungsi tidak dikenal: ${t.name}`);
        if (st.length < argc) throw new Error(`Fungsi ${t.name} kekurangan argumen`);
        const args = st.splice(st.length - argc, argc);
        const res = impl.apply(null, args);
        if (!Number.isFinite(res)) throw new Error(`Fungsi ${t.name} menghasilkan nilai tidak valid`);
        st.push(res);
        continue;
      }
      throw new Error('Token RPN tidak didukung');
    }
    if (st.length !== 1) throw new Error('Ekspresi tidak valid');
    return st[0];
  }

  function evaluate(expr, variables = {}, opts = {}) {
    if (expr == null || String(expr).trim() === '') throw new Error('Ekspresi kosong');
    const tokens = tokenize(expr);
    const rpn = toRpn(tokens);
    let v = evalRpn(rpn, variables || {});
    if (opts && opts.clampMinZero) v = Math.max(0, v);
    return v;
  }

  G.VolFormula = { evaluate };

})();
