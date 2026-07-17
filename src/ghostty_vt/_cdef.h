/*
 * Generated cdef for the libghostty-vt raw layer. DO NOT EDIT BY HAND.
 *
 * Produced from the vendored upstream headers by tools/gen_cdef.
 * Regenerate with `just gen-cdef` (after `just vendor`).
 *
 * Pinned upstream commit: 73534c4680a809398b396c94ac7f12fcccb7963d
 * Headers: ghostty/vt/types.h, ghostty/vt/allocator.h, ghostty/vt/build_info.h, ghostty/vt/device.h, ghostty/vt/sys.h
 */

/* ---- ghostty/vt/types.h ---- */
typedef enum {
    GHOSTTY_SUCCESS = 0,
    GHOSTTY_OUT_OF_MEMORY = -1,
    GHOSTTY_INVALID_VALUE = -2,
    GHOSTTY_OUT_OF_SPACE = -3,
    GHOSTTY_NO_VALUE = -4,
    GHOSTTY_RESULT_MAX_VALUE = 2147483647,
} GhosttyResult;
typedef struct GhosttyTerminalImpl* GhosttyTerminal;
typedef struct GhosttyTrackedGridRefImpl* GhosttyTrackedGridRef;
typedef struct GhosttyKittyGraphicsImpl* GhosttyKittyGraphics;
typedef const struct GhosttyKittyGraphicsImageImpl* GhosttyKittyGraphicsImage;
typedef struct GhosttyKittyGraphicsPlacementIteratorImpl* GhosttyKittyGraphicsPlacementIterator;
typedef struct GhosttyRenderStateImpl* GhosttyRenderState;
typedef struct GhosttyRenderStateRowIteratorImpl* GhosttyRenderStateRowIterator;
typedef struct GhosttyRenderStateRowCellsImpl* GhosttyRenderStateRowCells;
typedef struct GhosttySgrParserImpl* GhosttySgrParser;
typedef struct GhosttyFormatterImpl* GhosttyFormatter;
typedef struct GhosttyOscParserImpl* GhosttyOscParser;
typedef struct GhosttyOscCommandImpl* GhosttyOscCommand;
typedef enum {
  GHOSTTY_FORMATTER_FORMAT_PLAIN,
  GHOSTTY_FORMATTER_FORMAT_VT,
  GHOSTTY_FORMATTER_FORMAT_HTML,
  GHOSTTY_FORMATTER_FORMAT_MAX_VALUE = 2147483647,
} GhosttyFormatterFormat;
typedef struct {
  const uint8_t* ptr;
  size_t len;
} GhosttyString;
typedef struct {
  uint8_t* ptr;
  size_t cap;
  size_t len;
} GhosttyBuffer;
typedef struct {
  double x;
  double y;
} GhosttySurfacePosition;
typedef struct {
  const uint32_t* ptr;
  size_t len;
} GhosttyCodepoints;
            const char *ghostty_type_json(void);

/* ---- ghostty/vt/allocator.h ---- */
typedef struct {
    void* (*alloc)(void *ctx, size_t len, uint8_t alignment, uintptr_t ret_addr);
    bool (*resize)(void *ctx, void *memory, size_t memory_len, uint8_t alignment, size_t new_len, uintptr_t ret_addr);
    void* (*remap)(void *ctx, void *memory, size_t memory_len, uint8_t alignment, size_t new_len, uintptr_t ret_addr);
    void (*free)(void *ctx, void *memory, size_t memory_len, uint8_t alignment, uintptr_t ret_addr);
} GhosttyAllocatorVtable;
typedef struct GhosttyAllocator {
    void *ctx;
    const GhosttyAllocatorVtable *vtable;
} GhosttyAllocator;
            uint8_t* ghostty_alloc(const GhosttyAllocator* allocator, size_t len);
            void ghostty_free(const GhosttyAllocator* allocator, uint8_t* ptr, size_t len);

/* ---- ghostty/vt/build_info.h ---- */
typedef enum {
  GHOSTTY_OPTIMIZE_DEBUG = 0,
  GHOSTTY_OPTIMIZE_RELEASE_SAFE = 1,
  GHOSTTY_OPTIMIZE_RELEASE_SMALL = 2,
  GHOSTTY_OPTIMIZE_RELEASE_FAST = 3,
  GHOSTTY_OPTIMIZE_MODE_MAX_VALUE = 2147483647,
} GhosttyOptimizeMode;
typedef enum {
  GHOSTTY_BUILD_INFO_INVALID = 0,
  GHOSTTY_BUILD_INFO_SIMD = 1,
  GHOSTTY_BUILD_INFO_KITTY_GRAPHICS = 2,
  GHOSTTY_BUILD_INFO_TMUX_CONTROL_MODE = 3,
  GHOSTTY_BUILD_INFO_OPTIMIZE = 4,
  GHOSTTY_BUILD_INFO_VERSION_STRING = 5,
  GHOSTTY_BUILD_INFO_VERSION_MAJOR = 6,
  GHOSTTY_BUILD_INFO_VERSION_MINOR = 7,
  GHOSTTY_BUILD_INFO_VERSION_PATCH = 8,
  GHOSTTY_BUILD_INFO_VERSION_PRE = 9,
  GHOSTTY_BUILD_INFO_VERSION_BUILD = 10,
  GHOSTTY_BUILD_INFO_MAX_VALUE = 2147483647,
} GhosttyBuildInfo;
            GhosttyResult ghostty_build_info(GhosttyBuildInfo data, void *out);

/* ---- ghostty/vt/device.h ---- */
typedef enum {
    GHOSTTY_COLOR_SCHEME_LIGHT = 0,
    GHOSTTY_COLOR_SCHEME_DARK = 1,
    GHOSTTY_COLOR_SCHEME_MAX_VALUE = 2147483647,
} GhosttyColorScheme;
typedef struct {
    uint16_t conformance_level;
    uint16_t features[64];
    size_t num_features;
} GhosttyDeviceAttributesPrimary;
typedef struct {
    uint16_t device_type;
    uint16_t firmware_version;
    uint16_t rom_cartridge;
} GhosttyDeviceAttributesSecondary;
typedef struct {
    uint32_t unit_id;
} GhosttyDeviceAttributesTertiary;
typedef struct {
    GhosttyDeviceAttributesPrimary primary;
    GhosttyDeviceAttributesSecondary secondary;
    GhosttyDeviceAttributesTertiary tertiary;
} GhosttyDeviceAttributes;

/* ---- ghostty/vt/sys.h ---- */
typedef struct {
    uint32_t width;
    uint32_t height;
    uint8_t* data;
    size_t data_len;
} GhosttySysImage;
typedef enum {
    GHOSTTY_SYS_LOG_LEVEL_ERROR = 0,
    GHOSTTY_SYS_LOG_LEVEL_WARNING = 1,
    GHOSTTY_SYS_LOG_LEVEL_INFO = 2,
    GHOSTTY_SYS_LOG_LEVEL_DEBUG = 3,
    GHOSTTY_SYS_LOG_LEVEL_MAX_VALUE = 2147483647,
} GhosttySysLogLevel;
typedef void (*GhosttySysLogFn)(
    void* userdata,
    GhosttySysLogLevel level,
    const uint8_t* scope,
    size_t scope_len,
    const uint8_t* message,
    size_t message_len);
typedef bool (*GhosttySysDecodePngFn)(
    void* userdata,
    const GhosttyAllocator* allocator,
    const uint8_t* data,
    size_t data_len,
    GhosttySysImage* out);
typedef enum {
    GHOSTTY_SYS_OPT_USERDATA = 0,
    GHOSTTY_SYS_OPT_DECODE_PNG = 1,
    GHOSTTY_SYS_OPT_LOG = 2,
    GHOSTTY_SYS_OPT_MAX_VALUE = 2147483647,
} GhosttySysOption;
            GhosttyResult ghostty_sys_set(GhosttySysOption option,
                                           const void* value);
            void ghostty_sys_log_stderr(void* userdata,
                                         GhosttySysLogLevel level,
                                         const uint8_t* scope,
                                         size_t scope_len,
                                         const uint8_t* message,
                                         size_t message_len);
