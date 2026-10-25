-- Restore account 1780243636 (coder) after an accidental tombstone deletion.
-- Source of truth: /root/backups/account-1780243636-20261023-182758.csv
-- Everything runs in one transaction; a failed statement leaves the DB untouched.
\set ON_ERROR_STOP on

BEGIN;

-- 1. identity / profile / premium / emoji status back to the pre-delete snapshot
UPDATE users SET
    phone                      = '8613888888888',
    first_name                 = 'sʜᴀᴘɪᴛᴏɢʀᴀᴍ-ᴄᴏᴅᴇʀ',
    last_name                  = '',
    username                   = 'shapitogramowner',
    country_code               = '',
    verified                   = true,
    about                      = '',
    last_seen_at               = 1792780070,
    premium_expires_at         = '2027-01-18 22:06:09+00',
    emoji_status_document_id   = 426249927907803741,
    emoji_status_collectible_id= 9200000000001089,
    emoji_status_collectible   = $json${"slug": "official-5870972044522291836-8", "title": "Input Key", "edge_color": 8159370, "text_color": 14344162, "document_id": 426249927907803741, "center_color": 10725557, "pattern_color": 4146512, "collectible_id": 9200000000001089, "pattern_document_id": 2644360950141433386}$json$::jsonb,
    deleted_at                 = NULL,
    deletion_source            = '',
    deletion_reason            = '',
    account_delete_at          = NULL,
    updated_at                 = now()
WHERE id = 1780243636;

-- 2. primary username becomes resolvable again
UPDATE peer_usernames
   SET active = true, updated_at = now()
 WHERE username_lower = 'shapitogramowner' AND peer_id = 1780243636;

-- 3. avatar back
UPDATE profile_photos
   SET active = true
 WHERE owner_peer_type = 'user' AND owner_peer_id = 1780243636
   AND photo_id = 2451784588110934136;

-- 4. the four collectible usernames return from the vault
UPDATE collectible_usernames
   SET status = 'owned', owner_peer_type = 'user', owner_peer_id = 1780243636,
       updated_at = now()
 WHERE id IN (78, 80, 81, 82) AND original_owner_peer_id = 1780243636;

INSERT INTO peer_usernames
    (username_lower, peer_type, peer_id, updated_at, username, active, editable, sort_order, collectible_id)
SELECT lower(cu.username), 'user', 1780243636, now(), cu.username, true, false, 0, cu.id
  FROM collectible_usernames cu
 WHERE cu.id IN (78, 80, 81, 82)
   AND NOT EXISTS (SELECT 1 FROM peer_usernames p WHERE p.username_lower = lower(cu.username));

-- 5. bot boot_bot: user row and bots row
UPDATE users SET
    username = 'boot_bot', first_name = 'boot_bot',
    deleted_at = NULL, deletion_source = '', deletion_reason = '',
    updated_at = now()
 WHERE id = 1780243670;

INSERT INTO bots
    (bot_user_id, owner_user_id, token_secret, description, commands,
     bot_chat_history, bot_nochats, inline_placeholder, created_at, updated_at,
     menu_button_type, menu_button_text, menu_button_url, bot_inline_geo, can_debit_stars)
VALUES
    (1780243670, 1780243636, 'QhAed_yd1h43cqqWFCO3wlNmc1Fz2jcxYta', '', '[]',
     false, false, '', '2026-10-21 14:27:57.378373+00', '2026-10-21 14:27:57.378373+00',
     0, '', '', false, true)
ON CONFLICT (bot_user_id) DO UPDATE
   SET owner_user_id = EXCLUDED.owner_user_id,
       token_secret  = EXCLUDED.token_secret,
       updated_at    = now();

INSERT INTO peer_usernames
    (username_lower, peer_type, peer_id, updated_at, username, active, editable, sort_order)
SELECT 'boot_bot', 'user', 1780243670, now(), 'boot_bot', true, true, 0
 WHERE NOT EXISTS (SELECT 1 FROM peer_usernames WHERE username_lower = 'boot_bot');

COMMIT;

\echo '=== VERIFY'
SELECT id, username, first_name, phone, verified, premium_expires_at,
       deleted_at, deletion_source, emoji_status_collectible_id
  FROM users WHERE id = 1780243636;
SELECT bot_user_id, owner_user_id, can_debit_stars FROM bots WHERE bot_user_id = 1780243670;
SELECT id, username, status, owner_peer_id FROM collectible_usernames WHERE id IN (78,80,81,82) ORDER BY id;
SELECT username_lower, active FROM peer_usernames WHERE username_lower IN ('shapitogramowner','shapitogramcoder','cryptobot','shapitogram_xyz','snos','boot_bot') ORDER BY 1;
SELECT owner_peer_id, photo_id, active FROM profile_photos WHERE owner_peer_id = 1780243636;
