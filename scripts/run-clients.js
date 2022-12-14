const { exec } = require('child_process');
const wait = require('util').promisify(setTimeout);

const time = (() => {
    /** @type {Map<string, [number, number]} */
    const timeMap = new Map();

    /**
     *
     * @param {Object} data
     * @param {string} data.label
     * @param {'set'|'get'} data.type
     * @returns {number|undefined}
     */
    const func = data => {
        switch (data.type) {
            case 'set': {
                timeMap.set(data.label, process.hrtime());
                return undefined;
            }
            case 'get': {
                const oldTime = timeMap.get(data.label);
                if (!oldTime) return undefined;
                const curTime = process.hrtime(oldTime);
                const seconds = (curTime[0] * 1e9 + curTime[1]) / 1e9;
                return seconds;
            }
            default: {
                throw new Error(`Provided type is invalid: ${data.type}`);
            }
        }
    };

    return func;
})();

const random = (lo, hi) => Math.floor(Math.random() * (hi - lo + 1) + lo);

const config = {
    inputFile: 'Thread/Dostoyevsky.txt',
};

(async () => {
    let hostName, portNum, maxDelay = 0, clientNum = 1;
    let runExpect = process.argv.some(val => val === '-e');
    let clientType = process.argv.some(val => val === '-event') ? 'Event' : 'Thread'
    if (process.argv.length > 4) {
        hostName = process.argv[2];
        portNum = process.argv[3];
        if (process.argv[4])
            clientNum = parseInt(process.argv[4]);
        if (process.argv[5])
            maxDelay = parseInt(process.argv[5]);
    } else {
        console.log('Must provide the hostname and port number');
        return;
    }

    for (let i = 0; i < clientNum; i++) {
        const delay = random(0, maxDelay);
        wait(delay).then(() => {
            let prog;
            if (runExpect) {
                prog = exec(`expect scripts/expect/Dostoyevsky.exp ${clientType}/client ${hostName} ${portNum}`);
            } else {
                prog = exec(`${clientType}/client ${hostName} ${portNum} < ${config.inputFile}`);
            }

            console.log(`Executing ${i}`);
            time({ label: `${i}`, type: 'set' });

            prog.once('spawn', code => {
                console.log(`Spawned ${i}`);
            });

            prog.once('close', code => {
                const seconds = time({ label: `${i}`, type: 'get' });
                console.log(`client ${i} (${code}): ${seconds}`);
            });

            prog.once('error', err => {
                console.log(err);
            });
        });
    }
})();
