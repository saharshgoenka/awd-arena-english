export const submissionReasonLabel = (reason: unknown): string => {
  switch (reason) {
    case 'invalid_flag':
      return 'Invalid flag'
    case 'own_flag':
      return 'Submitted own flag'
    case 'missing_target_player':
      return 'Missing target_player_id (legacy rule)'
    case 'target_mismatch':
      return 'target_player_id does not match flag owner (legacy rule)'
    case 'flag_already_claimed_by_attacker':
      return 'Flag already claimed by this player'
    case 'success':
      return 'Success'
    default:
      return String(reason ?? 'unknown')
  }
}
