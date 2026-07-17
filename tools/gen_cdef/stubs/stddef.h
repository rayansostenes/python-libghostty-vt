/*
 * Empty stub replacing the real <stddef.h> during cdef generation.
 *
 * The generator preprocesses the vendored headers with -nostdinc so system
 * headers do not leak compiler-internal typedefs and builtins into the output.
 * cffi's cdef parser already knows size_t, ptrdiff_t and friends as primitive
 * types, so this stub deliberately declares nothing.
 */
