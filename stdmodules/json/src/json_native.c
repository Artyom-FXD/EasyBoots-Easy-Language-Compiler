/**
 * json_native.c — Native C implementation for the JSON module.
 *
 * Provides JSON parsing (string→ely_value*) and serialization (ely_value*→string).
 * Uses Ely runtime functions (ely_dictify, ely_value_to_json, etc.) from ely_runtime.h.
 */
#include <string.h>
#include "../../runtime/ely_runtime.h"

/* ---------------- Public API ---------------- */

/**
 * json_parse_str — Parse a JSON string and return an ely_value* tree.
 * Uses the runtime's ely_dictify + ely_value_from_json.
 */
ely_value* json_parse_str(const char* s) {
    if (!s) return ely_value_new_null();
    return ely_value_from_json(s, NULL);
}

/**
 * json_value_to_str — Serialize an ely_value* to a JSON string.
 * Uses the runtime's ely_value_to_json.
 */
char* json_value_to_str(void* value) {
    if (!value) return ely_str_dup("null");
    return ely_value_to_json((ely_value*)value);
}

/**
 * json_is_valid — Check if a string is valid JSON.
 * Returns 1 if valid, 0 otherwise.
 */
int json_is_valid(const char* s) {
    if (!s) return 0;
    ely_value* v = ely_value_from_json(s, NULL);
    if (v && v->type != ely_VALUE_NULL) return 1;
    /* edge case: "null" is valid JSON */
    if (v && v->type == ely_VALUE_NULL) {
        /* check if the string literally was "null" */
        const char* p = s;
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r') p++;
        if (strncmp(p, "null", 4) == 0) return 1;
    }
    return 0;
}