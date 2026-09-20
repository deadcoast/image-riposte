# Documentation map

Start with [the main README](../README.md) for operation and
[Current workflow and data contract](CURRENT-CONTRACT.md) for privacy, consent,
recovery and the exact replacements for older claims. Source defines implemented
behavior; a historical heading or passing old report is not current acceptance.

## Current guides

| Need | Maintained guide |
| --- | --- |
| Commands, menus and recovery actions | [CLI](CLI.md), [UX contract](UX-CONTRACT.md) |
| Public images, private originals and date-only scope | [Current contract](CURRENT-CONTRACT.md#public-outputs-versus-private-state), [threat model](THREAT-MODEL.md) |
| Selected-input protection, review and packs | [Publishing](PUBLISHING.md) |
| Duplicate labels, confidence and report exports | [Duplicate Finder](DUPLICATES.md) |
| Install, launch, tests and build | [Rebuild](REBUILD.md) |
| Implemented work and qualification limits | [Project status](PROJECT-STATUS.md), [changelog](CHANGELOG.md) |
| Outstanding development and exact checkpoints | [todo-audit.PACER.md](../todo-audit.PACER.md) and the guarded PACER registers |
| Research claims and their evidence | [PCUC](PCUC.md), [sorting research review](research/sorting/RIPOSTE-REVIEW.md) |

Research files describe proposals and findings. Their presence does not imply
integration or effectiveness; follow their source/test/evidence links.

## Historical specifications and records

These records remain available for provenance. Follow the
[claim-by-claim supersession table](CURRENT-CONTRACT.md#superseded-historical-claims)
before applying their instructions to this checkout.

| Historical record | Boundary |
| --- | --- |
| [Development specification](DEVELOPMENT-SPEC.md) | Earlier delivery contracts; original body retained beneath a current supersession wrapper. |
| [Wave 04](WAVE-04.md), [terminal 0.5 specification](TERMINAL-DESIGN.spec.md) | Original interface/design bodies retained; current menus and evidence are linked in their wrappers. |
| [0.2 README](HISTORY-v02-README.md), [engine 0.2](ENGINE-v02.md), [engine 0.3](ENGINE-v03.md) | Earlier engine/lifecycle contracts; private undo history and independent workflows were added later. |
| [Wave 02 plan](WAVE-02-PLAN.md), [Wave 03 handoff](WAVE-03-HANDOFF.md), [expansion](01EXPANSION.md), [UI design](UI-DESIGN.md) | Design/planning provenance, not implementation proof. |
| [0.5 revision](REVISION-v05.md), [selective merge](PATCH-v05-MERGE.md), [validation](VALIDATION.md) | Evidence and acceptance at their recorded versions; do not substitute for current stage results. |

The [PAC-039 evidence](../evidence/documentation-contracts/README.md) retains the
pre-edit documents and verifies that archived files and historical bodies remain
byte-identical. New annotations change navigation, not the historical record.
