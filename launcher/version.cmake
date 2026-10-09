# 增强版显示后缀不能进入 Windows 数值版本和 manifest。
if (NOT PYSTAND_APP_VERSION)
    set(PYSTAND_APP_VERSION "0.0.0")
endif()

if (NOT PYSTAND_APP_VERSION MATCHES "^[0-9]+\\.[0-9]+\\.[0-9]+(-?rc[0-9]+)?(\\+plus\\.[0-9]+)?$")
    message(FATAL_ERROR "Invalid application version: ${PYSTAND_APP_VERSION}")
endif()

string(REGEX MATCH "^[0-9]+\\.[0-9]+\\.[0-9]+" _numeric_version "${PYSTAND_APP_VERSION}")
string(REPLACE "." ";" _ver_parts "${_numeric_version}")
list(APPEND _ver_parts "0")
list(JOIN _ver_parts "," APP_VER_CSV)
list(JOIN _ver_parts "." APP_VER_STR)

message(STATUS "PyStand 版本: ${PYSTAND_APP_VERSION} (numeric: ${APP_VER_STR})")
file(WRITE "${CMAKE_CURRENT_BINARY_DIR}/version.h"
    "// Generated from application version; do not edit.\n"
    "#define APP_VER_CSV ${APP_VER_CSV}\n"
    "#define APP_VER_STR \"${APP_VER_STR}\"\n"
    "#define APP_DISPLAY_VERSION \"${PYSTAND_APP_VERSION}\"\n"
)
