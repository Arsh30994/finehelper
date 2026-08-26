// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * TrustMesh — thin-file Trust Score attestation.
 * Stores hashes only (no PII, no raw UPI). Issuer-controlled for demos.
 */
contract TrustAttestation {
    address public issuer;

    struct Attestation {
        bytes32 userIdHash;
        bytes32 scoreHash;
        bytes32 signalsRoot;
        string modelVersion;
        uint64 attestedAt;
    }

    mapping(bytes32 => Attestation[]) private _history;
    event Attested(
        bytes32 indexed userIdHash,
        bytes32 scoreHash,
        bytes32 signalsRoot,
        string modelVersion,
        uint64 attestedAt
    );

    modifier onlyIssuer() {
        require(msg.sender == issuer, "not issuer");
        _;
    }

    constructor() {
        issuer = msg.sender;
    }

    function transferIssuer(address next) external onlyIssuer {
        require(next != address(0), "zero");
        issuer = next;
    }

    function attest(
        bytes32 userIdHash,
        bytes32 scoreHash,
        bytes32 signalsRoot,
        string calldata modelVersion
    ) external onlyIssuer {
        uint64 ts = uint64(block.timestamp);
        _history[userIdHash].push(
            Attestation({
                userIdHash: userIdHash,
                scoreHash: scoreHash,
                signalsRoot: signalsRoot,
                modelVersion: modelVersion,
                attestedAt: ts
            })
        );
        emit Attested(userIdHash, scoreHash, signalsRoot, modelVersion, ts);
    }

    function count(bytes32 userIdHash) external view returns (uint256) {
        return _history[userIdHash].length;
    }

    function latest(bytes32 userIdHash) external view returns (Attestation memory) {
        uint256 n = _history[userIdHash].length;
        require(n > 0, "none");
        return _history[userIdHash][n - 1];
    }
}
