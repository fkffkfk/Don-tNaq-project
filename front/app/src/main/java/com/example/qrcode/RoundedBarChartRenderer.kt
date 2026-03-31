package com.example.qrcode

import android.graphics.Canvas
import android.graphics.Path
import android.graphics.RectF
import com.github.mikephil.charting.animation.ChartAnimator
import com.github.mikephil.charting.interfaces.dataprovider.BarDataProvider
import com.github.mikephil.charting.interfaces.datasets.IBarDataSet
import com.github.mikephil.charting.renderer.BarChartRenderer
import com.github.mikephil.charting.utils.Transformer
import com.github.mikephil.charting.utils.Utils
import com.github.mikephil.charting.utils.ViewPortHandler

class RoundedBarChartRenderer(
    chart: BarDataProvider,
    animator: ChartAnimator,
    viewPortHandler: ViewPortHandler,
    private val radiusDp: Float = 8f
) : BarChartRenderer(chart, animator, viewPortHandler) {

    private val rect = RectF()
    private val radiusPx = Utils.convertDpToPixel(radiusDp)
    private val path = Path()

    override fun drawDataSet(c: Canvas, dataSet: IBarDataSet, index: Int) {
        val trans: Transformer = mChart.getTransformer(dataSet.axisDependency)
        val buffer = mBarBuffers[index]
        buffer.setPhases(mAnimator.phaseX, mAnimator.phaseY)
        buffer.setDataSet(index)
        buffer.setInverted(mChart.isInverted(dataSet.axisDependency))
        buffer.setBarWidth(mChart.barData.barWidth)
        buffer.feed(dataSet)
        trans.pointValuesToPixel(buffer.buffer)
        val phaseX = mAnimator.phaseX
        val phaseY = mAnimator.phaseY
        val barWidth = mChart.barData.barWidth

        mBarBorderPaint.color = dataSet.barBorderColor
        mBarBorderPaint.strokeWidth = Utils.convertDpToPixel(dataSet.barBorderWidth)

        val cnt = (dataSet.entryCount * phaseX).toInt().coerceAtMost(dataSet.entryCount)
        for (i in 0 until cnt) {
            val e = dataSet.getEntryForIndex(i)
            val x = e.x
            val y = e.y * phaseY

            // 논리좌표 (0이 축선)
            val left = x - barWidth / 2f
            val right = x + barWidth / 2f
            val top: Float
            val bottom: Float
            val roundTop: Boolean

            if (y >= 0f) {
                // 양수: 위쪽이 막대의 끝 → 위쪽만 둥글게
                top = y
                bottom = 0f
                roundTop = true
            } else {
                // 음수: 아래쪽이 막대의 끝 → 아래쪽만 둥글게
                top = 0f
                bottom = y
                roundTop = false
            }

            rect.set(left, top, right, bottom)
            trans.rectToPixelPhase(rect, phaseY)

            // 각 코너별 반경 지정 (tl, tr, br, bl 순서로 x,y 쌍)
            val radii = if (roundTop) {
                floatArrayOf(
                    radiusPx, radiusPx,   // top-left
                    radiusPx, radiusPx,   // top-right
                    0f, 0f,               // bottom-right
                    0f, 0f                // bottom-left
                )
            } else {
                floatArrayOf(
                    0f, 0f,               // top-left
                    0f, 0f,               // top-right
                    radiusPx, radiusPx,   // bottom-right
                    radiusPx, radiusPx    // bottom-left
                )
            }

            // Path로 “윗부분만(또는 아랫부분만)” 둥글리기
            path.reset()
            path.addRoundRect(rect, radii, Path.Direction.CW)

            mRenderPaint.color = dataSet.getColor(i)
            c.drawPath(path, mRenderPaint)

            if (dataSet.barBorderWidth > 0f) {
                c.drawPath(path, mBarBorderPaint)
            }
        }
    }
}

