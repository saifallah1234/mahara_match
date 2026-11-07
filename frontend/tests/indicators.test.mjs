// Placement: frontend/tests/indicators.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { largestGaps } from '../src/lib/indicators.ts'

const gap = (skill, offer_demand, training_supply) => ({ skill, offer_demand, training_supply })

test('the three largest gaps come first, largest shortfall of training places first', () => {
  const gaps = [gap('Excel', 3, 3), gap('Python', 9, 1), gap('SQL', 5, 4), gap('Java', 6, 0), gap('Docker', 4, 1)]
  assert.deepEqual(largestGaps(gaps).map((g) => g.skill), ['Python', 'Java', 'Docker'])
})

test('skills already covered by training are not highlighted as gaps', () => {
  assert.deepEqual(largestGaps([gap('Excel', 2, 2), gap('Word', 1, 5), gap('SQL', 2, 1)]).map((g) => g.skill), ['SQL'])
  assert.deepEqual(largestGaps([]), [])
})
