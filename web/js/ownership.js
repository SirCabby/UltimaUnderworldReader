/**
 * Centralized ownership semantics for the web UI.
 *
 * The raw UW object "owner" field is used for multiple unrelated purposes:
 * - NPC ownership (stealing)
 * - keys (lock id)
 * - trap/trigger parameters
 * - animation internal state
 * - special-case quest identification
 *
 * This module defines what "owned" means for UI display and filtering.
 */
(function initOwnership(global) {
    'use strict';

    // Explicit object IDs that must never show/behave as "owned" in the UI.
    // (These may still use the raw owner field for other purposes in game data.)
    const NEVER_OWNED_OBJECT_IDS = new Set([
        0x1CA, // 458 - silver tree (quest item, owner used for special cases)

        0x0C2, // skull
        0x0C3, // skull (variant)
        0x0C4, // bones
        0x0C5, // bones (variant)
        0x0C6, // pile of bones (also used for Garamon's bones identification)
        0x0DC, // pile of bones (variant)
    ]);

    const NEVER_OWNED_CATEGORIES = new Set([
        // World mechanics / non-loot
        'trap', 'traps',
        'trigger', 'triggers',
        'animation', 'animations',
        'stairs',

        // Secrets / world-only
        'secret_door', 'secret_doors',

        // Stationary decals/text (owner often used as parameters/indexing)
        'writings',

        // Scenery junk (even if it has an owner field set)
        'useless_item',
    ]);

    function toNumberOrNull(v) {
        if (v === undefined || v === null || v === '') return null;
        if (typeof v === 'number') return Number.isFinite(v) ? v : null;
        const n = Number(v);
        return Number.isFinite(n) ? n : null;
    }

    function getObjectId(item) {
        if (!item) return null;
        // Prefer explicit object_id; fall back to object_id_hex if present.
        const objId = toNumberOrNull(item.object_id);
        if (objId !== null) return objId;
        const hex = item.object_id_hex;
        if (typeof hex === 'string' && hex.length > 0) {
            // Accept "0x1CA" or "1CA".
            const cleaned = hex.startsWith('0x') || hex.startsWith('0X') ? hex : `0x${hex}`;
            const parsed = Number.parseInt(cleaned, 16);
            return Number.isFinite(parsed) ? parsed : null;
        }
        return null;
    }

    function getCategory(item) {
        if (!item) return '';
        return (item.category || '').toString();
    }

    function isSecretType(item) {
        if (!item) return false;
        return item.type === 'secret_door' || item.type === 'illusory_wall';
    }

    /**
     * True if this object should never be treated as "owned" (UI semantics),
     * even if the raw owner field is non-zero.
     */
    function isNeverOwned(item) {
        if (!item) return true;

        // Secrets are never owned.
        if (isSecretType(item)) return true;

        const objId = getObjectId(item);
        if (objId !== null) {
            if (NEVER_OWNED_OBJECT_IDS.has(objId)) return true;

            // Keys: owner field is lock id, not NPC ownership.
            if (objId >= 0x100 && objId <= 0x10E) return true;

            // Texture map objects: owner/quality are parameters.
            if (objId === 0x16E || objId === 0x16F) return true;

            // Switches: owner is linking/parameters, not ownership.
            if (objId >= 0x170 && objId <= 0x17F) return true;

            // Traps and triggers: owner/quality are parameters.
            if (objId >= 0x180 && objId <= 0x19F) return true;
            if (objId >= 0x1A0 && objId <= 0x1BF) return true;

            // Animations: owner is internal state.
            if ((objId >= 0x1C0 && objId <= 0x1C9) || (objId >= 0x1CB && objId <= 0x1CF)) return true;
        }

        const category = getCategory(item);
        if (category && NEVER_OWNED_CATEGORIES.has(category)) return true;

        return false;
    }

    /**
     * Semantic ownership for the UI: true only when the object is eligible and owner>0.
     */
    function isOwned(item) {
        if (!item) return false;
        if (isNeverOwned(item)) return false;
        const owner = toNumberOrNull(item.owner);
        return owner !== null && owner > 0;
    }

    global.Ownership = Object.freeze({
        isNeverOwned,
        isOwned,
        shouldShowOwner: isOwned,
    });
})(window);

