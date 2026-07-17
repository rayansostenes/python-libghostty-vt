/*
 * Empty stub replacing the real <stdint.h> during cdef generation.
 *
 * cffi's cdef parser knows the fixed-width integer types (uint8_t, int32_t,
 * uintptr_t, ...) as primitives, so leaving them undeclared here keeps the
 * generated cdef free of compiler-internal noise. See stddef.h for the rationale.
 */
