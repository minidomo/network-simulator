const fs = require('fs');

const SESSION_ID_REGEX = /^(0x[\dabcdef]+)/;
const SEQ_REGEX = /\[(\d+)\]/;
const FILE_LINES = 58936;
const DECIMAL_ROUND_OFF = 4;

(async () => {
    if (process.argv.length !== 3) {
        console.log('must provide a relative filename to analyze.');
        return;
    }
    const filePath = `${process.cwd()}/${process.argv[2]}`;
    console.log(`analyzing ${filePath}`);

    const data = fs.readFileSync(filePath, { encoding: 'utf-8' })
        .split(/[\r\n]+/)
        .map(line => line.trim());

    console.log(`total lines: ${data.length}`);

    const sessionIds = new Set();
    data.forEach(line => {
        const match = line.match(SESSION_ID_REGEX);
        if (match) {
            [, id] = match;
            sessionIds.add(id);
        }
    });

    console.log(`found ${sessionIds.size} session ids`);

    let totalLossCount = 0;
    const totalLines = FILE_LINES * sessionIds.size;

    sessionIds.forEach(id => {
        const lines = data.filter(line => line.startsWith(id));

        if (lines.length != FILE_LINES + 3) {
            /** @type {Set<number>} */
            const seqSet = new Set()
            lines.forEach(line => {
                const res = line.match(SEQ_REGEX);
                if (res) {
                    const [, seq] = res;
                    const seqNum = parseInt(seq);
                    seqSet.add(seqNum);
                }
            });

            const min = 0;
            const max = FILE_LINES + 1;
            /** @type {Set<number>} */
            const missingSeqSet = new Set()
            for (let i = min; i <= max; i++) {
                if (!seqSet.has(i)) {
                    missingSeqSet.add(i);
                }
            }

            let i = max;
            /** @type {Set<number>} */
            const copyMissingSeqSet = new Set(missingSeqSet);
            while (copyMissingSeqSet.has(i)) {
                copyMissingSeqSet.delete(i);
                i--;
            }

            if (copyMissingSeqSet.size > 0) {
                let s = '';
                missingSeqSet.forEach(val => s += `${val} `);
                console.log(`${id} - missing seq: ${s}`);
                return;
            }
        }

        const lostCount = lines.filter(line => line.match(/Lost packet!$/i)).length;
        const lossRate = lostCount / FILE_LINES * 100;
        console.log(`${id} loss rate (%): ${lossRate.toFixed(DECIMAL_ROUND_OFF)} (${lostCount} / ${FILE_LINES})`);

        totalLossCount += lostCount;
    });

    const totalLossRate = totalLossCount / totalLines * 100;

    console.log(`Average loss rate: ${totalLossRate.toFixed(DECIMAL_ROUND_OFF)} (${totalLossCount} / ${totalLines})`);
})();