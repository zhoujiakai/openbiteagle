#!/usr/bin/env python3
"""向知识库添加 Web3 示例文档。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.vector import insert_document


# Web3 示例文档
SAMPLE_DOCS = [
    {
        "title": "Bitcoin: Digital Gold Overview",
        "content": """Bitcoin (BTC) is the first and largest cryptocurrency by market capitalization. Created in 2009 by the pseudonymous Satoshi Nakamoto, Bitcoin introduced a revolutionary decentralized digital currency system based on blockchain technology.

Key Features:
- Limited Supply: Only 21 million bitcoins will ever exist, making it a deflationary asset
- Proof of Work: Mining secures the network and validates transactions
- Store of Value: Often referred to as "digital gold" due to its scarcity and adoption

Bitcoin is primarily used as a store of value and investment asset, with growing acceptance as a medium of exchange. Its price is heavily influenced by institutional adoption, regulatory news, and macroeconomic factors.""",
        "source_url": "https://example.com/bitcoin-overview",
        "source_type": "manual",
        "metadata": {"category": "cryptocurrency", "tokens": ["BTC", "Bitcoin"]},
    },
    {
        "title": "Ethereum: Smart Contract Platform",
        "content": """Ethereum (ETH) is a decentralized blockchain platform that enables smart contracts and decentralized applications (dApps). Launched in 2015 by Vitalik Buterin, Ethereum introduced programmable money and the concept of a "world computer".

Key Features:
- Smart Contracts: Self-executing contracts with the terms directly written into code
- ERC-20 Tokens: Standard for creating fungible tokens on Ethereum
- DeFi Ecosystem: Home to decentralized finance protocols
- Proof of Stake: Merged from PoW in 2022, reducing energy consumption by 99.95%

Ethereum's native token, Ether (ETH), is used to pay for transactions and computational services on the network. The platform hosts thousands of dApps including DeFi protocols, NFT marketplaces, and DAOs.""",
        "source_url": "https://example.com/ethereum-overview",
        "source_type": "manual",
        "metadata": {"category": "platform", "tokens": ["ETH", "Ethereum"]},
    },
    {
        "title": "Solana: High-Performance Blockchain",
        "content": """Solana (SOL) is a high-performance blockchain designed for scalability and fast transactions. Launched in 2020 by Anatoly Yakovenko, Solana aims to solve the blockchain trilemma of scalability, security, and decentralization.

Key Features:
- High Throughput: Capable of 65,000 transactions per second
- Low Fees: Average transaction fee of $0.00025
- Proof of History: Unique consensus mechanism for time coordination
- Rust-Based: Programs written in Rust or C for performance

Solana has become a popular alternative to Ethereum for DeFi applications, NFTs, and gaming due to its speed and low costs. However, it has faced criticism for network outages and perceived centralization.""",
        "source_url": "https://example.com/solana-overview",
        "source_type": "manual",
        "metadata": {"category": "platform", "tokens": ["SOL", "Solana"]},
    },
    {
        "title": "Uniswap: Decentralized Exchange Protocol",
        "content": """Uniswap is a decentralized exchange (DEX) protocol built on Ethereum that enables automated token swapping through liquidity pools. Founded in 2018 by Hayden Adams, Uniswap pioneered the automated market maker (AMM) model.

Key Features:
- AMM Model: Uses algorithmic liquidity pools instead of order books
- Liquidity Providers: Users earn fees by providing liquidity
- Governance: UNIP token holders vote on protocol changes
- V4: Latest version with concentrated liquidity and hooks

Uniswap is the largest DEX by trading volume and has expanded to multiple chains including Polygon, Arbitrum, and Optimism.""",
        "source_url": "https://example.com/uniswap-overview",
        "source_type": "manual",
        "metadata": {"category": "dex", "tokens": ["UNI", "ETH"]},
    },
    {
        "title": "Chainlink: Decentralized Oracle Network",
        "content": """Chainlink (LINK) is a decentralized oracle network that provides real-world data to smart contracts. Launched in 2017, Chainlink solves the "oracle problem" by enabling smart contracts to securely interact with external data.

Key Features:
- Price Feeds: Reliable price data for thousands of token pairs
- VRF: Verifiable random number generation for gaming and NFTs
- Cross-Chain: Supports multiple blockchain networks
- Data Feeds: Sports, weather, and other real-world events

Chainlink is essential for DeFi protocols that need accurate price data and for smart contracts that require external triggers. The LINK token is used to pay node operators for providing data services.""",
        "source_url": "https://example.com/chainlink-overview",
        "source_type": "manual",
        "metadata": {"category": "infrastructure", "tokens": ["LINK"]},
    },
]


async def main():
    """向知识库添加示例文档。"""
    print("=" * 60)
    print("向知识库添加示例文档")
    print("=" * 60)
    print()

    for i, doc in enumerate(SAMPLE_DOCS, 1):
        print(f"{i}. 正在添加: {doc['title']}")

        doc_id = await insert_document(
            title=doc["title"],
            content=doc["content"],
            source_url=doc.get("source_url"),
            source_type=doc["source_type"],
            metadata=doc.get("metadata", {}),
        )

        print(f"   ✅ 文档 ID: {doc_id}")
        print()

    print("=" * 60)
    print(f"✅ 已添加 {len(SAMPLE_DOCS)} 篇示例文档")
    print()
    print("下一步: 运行 'python scripts/process_embeddings.py' 创建向量嵌入")


if __name__ == "__main__":
    asyncio.run(main())
